from collections import namedtuple

import datetime
import pymongo
import random
import numpy

class PlayerAnalysis(namedtuple('PlayerAnalysis', [
  'id', 'titled', 'engine', 'gamesPlayed', 'closedReports', 'gameAnalyses', 'gamesActivation'])): # id = userId, engine = (True | False | None)
  def setEngine(self, engine):
    return PlayerAnalysis(
      id = self.id,
      titled = self.titled, 
      engine = engine, 
      gamesPlayed = self.gamesPlayed,
      closedReports = self.closedReports,
      gameAnalyses = self.gameAnalyses,
      gamesActivation = self.gamesActivation)

  def tensorInputMoves(self):
    return self.gameAnalyses.tensorInputMoves()

  def tensorInputChunks(self):
    return self.gameAnalyses.tensorInputChunks()

  def tensorInputMoveChunks(self):
    return self.gameAnalyses.tensorInputMoveChunks()

  def tensorInputGames(self):
    return self.gameAnalyses.binnedGameActivations() + self.gameAnalyses.proportionalBinnedGameActivations() + self.gameAnalyses.streaks() + self.gameAnalyses.proportionalStreaks() # list of 16 ints

  def moveActivations(self):
    return self.gameAnalyses.moveActivations()

  def chunkActivations(self):
    return self.gameAnalyses.chunkActivations()

  def CSVMoves(self):
    return [[int(self.engine)] + move for move in self.tensorInputMoves()]

  def CSVChunks(self):
    return [[int(self.engine)] + chunk for chunk in self.tensorInputChunks()]

  def CSVMoveChunks(self):
    return [[int(self.engine)] + game for game in self.tensorInputMoveChunks()]

  def CSVGames(self):
    return [int(self.engine)] + self.tensorInputGames()

  def report(self, thresholds):
    return {
      'userId': self.id,
      'isLegit': self.isLegit(thresholds),
      'activation': self.activation(),
      'pv0ByAmbiguity': self.gameAnalyses.pv0ByAmbiguityStats(),
      'games': self.gameAnalyses.reportDicts()
    }

  def activation(self):
    return max(min(int(self.gamesActivation), self.gameAnalyses.top3average()), self.gameAnalyses.averageActivation())

  def isLegit(self, thresholds):
    if self.activation is not None:
      gamesAnalysed = len(self.gameAnalyses.gameAnalyses)

      gameActivations = self.gameAnalyses.gameActivations()

      suspiciousGames = sum([int(a > thresholds['averages']['suspicious']) for a in gameActivations])
      #exceptionalGames = sum([int(a > thresholds['averages']['exceptional']) for a in gameActivations])

      if (not self.titled and self.activation() > thresholds['overall']['engine']
        and gamesAnalysed > 3):
        return False
      elif self.activation() < thresholds['overall']['legit'] and suspiciousGames == 0 and gamesAnalysed > 4:
        return True # Player is legit
    return None # Player falls into a grey area

class PlayerAnalysisBSONHandler:
  @staticmethod
  def reads(bson, gameAnalyses):
    return PlayerAnalysis(
      id = bson['_id'],
      titled = bson['titled'],
      engine = bson['engine'],
      gamesPlayed = bson['gamesPlayed'],
      closedReports = bson['closedReports'],
      gameAnalyses = gameAnalyses,
      gamesActivation = bson.get('gamesActivation', None))

  @staticmethod
  def writes(playerAnalysis):
    return {
      '_id': playerAnalysis.id,
      'titled': playerAnalysis.titled,
      'engine': playerAnalysis.engine,
      'gamesPlayed': playerAnalysis.gamesPlayed,
      'closedReports': playerAnalysis.closedReports,
      'gamesActivation': playerAnalysis.gamesActivation,
      'date': datetime.datetime.utcnow()
    }

class PlayerAnalysisDB:
  def __init__(self, playerAnalysisColl, gameAnalysisDB):
    self.playerAnalysisColl = playerAnalysisColl
    self.gameAnalysisDB = gameAnalysisDB

  def byId(self, userId):
    try:
      return PlayerAnalysisBSONHandler.reads(
        self.playerAnalysisColl.find_one({'_id': userId}),
        self.gameAnalysisDB.byUserId(userId))
    except:
      return None

  def byBSONs(self, bsons):
    return [PlayerAnalysisBSONHandler.reads(bson, self.gameAnalysisDB.byUserId(bson['_id'])) for bson in bsons]

  def byEngineStatus(self, status):
    return self.byBSONs(self.playerAnalysisColl.find({'engine': status}).sort('date', pymongo.DESCENDING).limit(2000))

  def byEngineStatusPaginated(self, status, page, nb):
    return self.byBSONs(self.playerAnalysisColl.find({'engine': status})[nb*page:nb*(page+1)])

  def oldestUnsorted(self):
    playerAnalysisBSON = next(self.playerAnalysisColl.find({'engine': None}).sort('date', pymongo.ASCENDING), None)
    if playerAnalysisBSON is not None:
      return PlayerAnalysisBSONHandler.reads(playerAnalysisBSON, self.gameAnalysisDB.byUserId(playerAnalysisBSON['_id']))
    return None

  def oldestUnsortedUserId(self):
    oldest = self.oldestUnsorted()
    if oldest is not None:
      return oldest.id
    return None

  def allUnsorted(self): # Players who have not been marked as Engine or Legit
    return self.byEngineStatus(None)

  def allSorted(self):
    return self.byBSONs(self.playerAnalysisColl.find({'engine': {'$in': [True, False]}}))

  def all(self):
    return self.byBSONs(self.playerAnalysisColl.find())

  def balancedSorted(self):
    enginePlayerAnalyses = self.engines()
    legitPlayerAnalyses = self.legits()
    amount = min(len(enginePlayerAnalyses), len(legitPlayerAnalyses))
    randomEngines = [ enginePlayerAnalyses[i] for i in sorted(random.sample(range(len(enginePlayerAnalyses)), amount)) ]
    randomLegits =  [ legitPlayerAnalyses[i] for i in sorted(random.sample(range(len(legitPlayerAnalyses)), amount)) ]
    return randomLegits + randomEngines

  def countUnsorted(self):
    return self.playerAnalysisColl.count({'engine': None})

  def engines(self):
    return self.byEngineStatus(True)

  def legits(self):
    return self.byEngineStatus(False)

  def enginesPaginated(self, page = 0, nb = 500):
    return self.byEngineStatusPaginated(True, page, nb)

  def legitsPaginated(self, page = 0, nb = 500):
    return self.byEngineStatusPaginated(False, page, nb)

  def write(self, playerAnalysis):
    self.playerAnalysisColl.update(
      {'_id': playerAnalysis.id},
      {'$set': PlayerAnalysisBSONHandler.writes(playerAnalysis)},
      upsert=True)
    self.gameAnalysisDB.lazyWriteGames(playerAnalysis.gameAnalyses)

  def lazyWriteMany(self, playerAnalyses):
    [self.write(playerAnalysis) for playerAnalysis in playerAnalyses]