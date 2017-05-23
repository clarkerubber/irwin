from collections import namedtuple

import datetime
import pymongo
import random
import numpy

class PlayerAnalysis(namedtuple('PlayerAnalysis', [
  'id', 'titled', 'engine', 'gamesPlayed', 'closedReports', 'gameAnalyses', 'gamesActivation', 'pvActivation'])): # id = userId, engine = (True | False | None)
  def setEngine(self, engine):
    return PlayerAnalysis(
      id = self.id,
      titled = self.titled, 
      engine = engine, 
      gamesPlayed = self.gamesPlayed,
      closedReports = self.closedReports,
      gameAnalyses = self.gameAnalyses,
      gamesActivation = self.gamesActivation,
      pvActivation = self.pvActivation)

  def activation(self):
    return int((self.gamesActivation + self.pvActivation) / 2)

  def tensorInputMoves(self):
    return self.gameAnalyses.tensorInputMoves()

  def tensorInputChunks(self):
    return self.gameAnalyses.tensorInputChunks()

  def tensorInputMoveChunks(self):
    return self.gameAnalyses.tensorInputMoveChunks()

  def tensorInputGamePVs(self):
    return self.gameAnalyses.tensorInputGamePVs()

  def tensorInputPVsDraw(self):
    return self.gameAnalyses.tensorInputPVsDraw()

  def tensorInputPVsLosing(self):
    return self.gameAnalyses.tensorInputPVsLosing()

  def tensorInputPV0ByAmbiguity(self):
    pvs = self.gameAnalyses.pv0ByAmbiguityStats()
    for i, pv in enumerate(pvs):
      if pv is None:
        pvs[i] = 0
    return pvs # list of ints 5 items long

  def tensorInputPlayerPVs(self):
    return self.tensorInputPV0ByAmbiguity() + self.tensorInputPVsDraw() + self.tensorInputPVsLosing() # 15 ints

  def tensorInputGames(self):
    return self.binnedGameActivations() # list of 5 ints

  def moveActivations(self):
    return self.gameAnalyses.moveActivations()

  def chunkActivations(self):
    return self.gameAnalyses.chunkActivations()

  def binnedGameActivations(self):
    return self.gameAnalyses.binnedGameActivations()

  def CSVMoves(self):
    moves = []
    [moves.append([int(self.engine)] + move) for move in self.tensorInputMoves()]
    return moves

  def CSVChunks(self):
    chunks = []
    [chunks.append([int(self.engine)] + chunk) for chunk in self.tensorInputChunks()]
    return chunks

  def CSVMoveChunks(self):
    games = []
    [games.append([int(self.engine)] + game) for game in self.tensorInputMoveChunks()]
    return games

  def CSVGamePVs(self):
    games = []
    [games.append([int(self.engine)] + game) for game in self.tensorInputGamePVs()]
    return games

  def CSVPlayerPVs(self):
    return [int(self.engine)] + self.tensorInputPlayerPVs()

  def CSVGames(self):
    return [int(self.engine)] + self.tensorInputGames()

  def report(self, thresholds):
    return {
      'userId': self.id,
      'isLegit': self.isLegit(thresholds),
      'activation': int(self.activation),
      'pv0ByAmbiguity': self.gameAnalyses.pv0ByAmbiguityStats(),
      'games': self.gameAnalyses.reportDicts()
    }

  def isLegit(self, thresholds):
    if self.activation() is not None:
      gamesAnalysed = len(self.gameAnalyses.gameAnalyses)

      gameActivations = self.gameAnalyses.gameActivations()

      moderateGames = sum([int(a > thresholds['averages']['moderate']) for a in gameActivations])
      exceptionalGames = sum([int(a > thresholds['averages']['exceptional']) for a in gameActivations])

      legitGames = sum([int(a < thresholds['averages']['legit']) for a in gameActivations])

      if (not self.titled and self.activation() > thresholds['overall']['engine']
        and exceptionalGames >= (2/10)*gamesAnalysed and exceptionalGames > 1
        and gamesAnalysed > 4):
        return False
      elif self.activation() < thresholds['overall']['legit'] and moderateGames == 0 and gamesAnalysed > 4:
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
      gamesActivation = bson.get('gamesActivation', None),
      pvActivation = bson.get('pvActivation', None))

  @staticmethod
  def writes(playerAnalysis):
    return {
      '_id': playerAnalysis.id,
      'titled': playerAnalysis.titled,
      'engine': playerAnalysis.engine,
      'gamesPlayed': playerAnalysis.gamesPlayed,
      'closedReports': playerAnalysis.closedReports,
      'gamesActivation': playerAnalysis.gamesActivation,
      'pvActivation': playerAnalysis.pvActivation,
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