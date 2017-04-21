from collections import namedtuple

import datetime
import pymongo
import random
import numpy

class PlayerAnalysis(namedtuple('PlayerAnalysis', ['id', 'titled', 'engine', 'gamesPlayed', 'closedReports', 'gameAnalyses'])): # id = userId, engine = (True | False | None)
  def setEngine(self, engine):
    return PlayerAnalysis(self.id, self.titled, engine, self.gamesPlayed, self.closedReports, self.gameAnalyses)

  def tensorInputMoves(self):
    moves = []
    [moves.extend(gameAnalysis.tensorInputMoves(self.titled)) for gameAnalysis in self.gameAnalyses.gameAnalyses]
    return moves

  def tensorInputChunks(self):
    chunks = []
    [chunks.extend(gameAnalysis.tensorInputChunks(self.titled)) for gameAnalysis in self.gameAnalyses.gameAnalyses]
    return chunks

  def CSVMoves(self):
    moves = []
    [moves.append([int(self.engine)] + move) for move in self.tensorInputMoves()]
    return moves

  def CSVChunks(self):
    chunks = []
    [chunks.append([int(self.engine)] + chunk) for chunk in self.tensorInputChunks()]
    return chunks

  def reason(self):
    if len(self.gameAnalyses.gameAnalyses) > 0:
      return "[BETA]\n"+"\n".join(['lichess.org/'+gameAnalysis.id+' AVERAGE: '+str(gameAnalysis.assessmentAverage())+'% OUTLIER AVG: '+str(gameAnalysis.assessmentOutlierAverage())+'%' for gameAnalysis in self.gameAnalyses.gameAnalyses])
    return "[BETA] No Games"

  def result(self):
    return sum([1 for g in self.gameAnalyses.gameAnalyses if g.assessmentAverage() > 60]) > 1

  def report(self):
    return {'result': False,
    'reason': self.reason()}

class PlayerAnalysisBSONHandler:
  @staticmethod
  def reads(bson, gameAnalyses):
    return PlayerAnalysis(
      id = bson['_id'],
      titled = bson['titled'],
      engine = bson['engine'],
      gamesPlayed = bson['gamesPlayed'],
      closedReports = bson['closedReports'],
      gameAnalyses = gameAnalyses)

  @staticmethod
  def writes(playerAnalysis):
    return {
      '_id': playerAnalysis.id,
      'titled': playerAnalysis.titled,
      'engine': playerAnalysis.engine,
      'gamesPlayed': playerAnalysis.gamesPlayed,
      'closedReports': playerAnalysis.closedReports,
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
    return self.byBSONs(self.playerAnalysisColl.find({'engine': status}))

  def oldestUnsorted(self):
    playerAnalysisBSON = next(self.playerAnalysisColl.find({'engine': None}).sort('date', pymongo.ASCENDING), None)
    if playerAnalysisBSON is not None:
      return PlayerAnalysisBSONHandler.reads(playerAnalysisBSON, self.gameAnalysisDB.byUserId(playerAnalysisBSON['_id']))
    return None

  def oldestUnsortedUserId(self):
    playerAnalysisBSON = next(self.playerAnalysisColl.find({'engine': None}).sort('date', pymongo.ASCENDING), None)
    if playerAnalysisBSON is not None:
      return playerAnalysisBSON['_id']
    return None

  def allUnsorted(self): # Players who have not been marked as Engine or Legit
    return self.byEngineStatus(None)

  def allSorted(self):
    return self.byBSONs(self.playerAnalysisColl.find({'engine': {'$in': [True, False]}}))

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

  def write(self, playerAnalysis):
    self.playerAnalysisColl.update(
      {'_id': playerAnalysis.id},
      {'$set': PlayerAnalysisBSONHandler.writes(playerAnalysis)},
      upsert=True)

  def lazyWriteMany(self, playerAnalyses):
    [self.write(playerAnalysis) for playerAnalysis in playerAnalyses]