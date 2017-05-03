from collections import namedtuple

import datetime
import pymongo
import random
import numpy

class PlayerAnalysis(namedtuple('PlayerAnalysis', ['id', 'titled', 'engine', 'gamesPlayed', 'closedReports', 'gameAnalyses', 'PVAssessment'])): # id = userId, engine = (True | False | None)
  def setEngine(self, engine):
    return PlayerAnalysis(
      id = self.id,
      titled = self.titled, 
      engine = engine, 
      gamesPlayed = self.gamesPlayed,
      closedReports = self.closedReports,
      gameAnalyses = self.gameAnalyses,
      PVAssessment = self.PVAssessment)

  def tensorInputMoves(self):
    return self.gameAnalyses.tensorInputMoves()

  def tensorInputChunks(self):
    return self.gameAnalyses.tensorInputChunks()

  def tensorInputPVs(self):
    pvs = self.gameAnalyses.pv0ByAmbiguityStats()
    for i, pv in enumerate(pvs):
      if pv is None:
        pvs[i] = 0
    return pvs # should be a list of ints 10 items long

  def CSVMoves(self):
    moves = []
    [moves.append([int(self.engine)] + move) for move in self.tensorInputMoves()]
    return moves

  def CSVChunks(self):
    chunks = []
    [chunks.append([int(self.engine)] + chunk) for chunk in self.tensorInputChunks()]
    return chunks

  def CSVPVs(self):
    return [int(self.engine)] + self.tensorInputPVs()

  def activation(self):
    anoa = sorted(self.gameAnalyses.assessmentNoOutlierAverages(), reverse=True)
    retained = anoa[min(1, int(0.3*len(anoa)))]
    return numpy.mean(retained)

  def report(self):
    return {
      'userId': self.id,
      'isLegit': self.isLegit(),
      'activation': int(self.activation()),
      'pv0ByAmbiguity': self.gameAnalyses.pv0ByAmbiguityStats(),
      'games': self.gameAnalyses.reportDicts()
    }

  def isLegit(self):
    gamesAnalysed = len(self.gameAnalyses.gameAnalyses)

    noOutlierAverages = self.gameAnalyses.assessmentNoOutlierAverages()

    susGames = sum([int(a > 60) for a in noOutlierAverages])
    verySusGames = sum([int(a > 75) for a in noOutlierAverages])

    legitGames = sum([int(a < 35) for a in noOutlierAverages])

    if ((verySusGames >= (1/5)*gamesAnalysed
        or susGames >= (2/5)*gamesAnalysed
        or (self.PVAssessment > 70 and susGames >= (1/5)*gamesAnalysed))
      and gamesAnalysed > 0 and not self.titled):
      return False
    elif legitGames == gamesAnalysed and self.PVAssessment < 30 and gamesAnalysed > 0:
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
      PVAssessment = bson.get('PVAssessment', None))

  @staticmethod
  def writes(playerAnalysis):
    return {
      '_id': playerAnalysis.id,
      'titled': playerAnalysis.titled,
      'engine': playerAnalysis.engine,
      'gamesPlayed': playerAnalysis.gamesPlayed,
      'closedReports': playerAnalysis.closedReports,
      'PVAssessment': playerAnalysis.PVAssessment,
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
    oldest = self.oldestUnsorted()
    if oldest is not None:
      return oldest.id
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
    self.gameAnalysisDB.lazyWriteGames(playerAnalysis.gameAnalyses)

  def lazyWriteMany(self, playerAnalyses):
    [self.write(playerAnalysis) for playerAnalysis in playerAnalyses]