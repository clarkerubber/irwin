from collections import namedtuple

import datetime
import pymongo
import random
import numpy

class PlayerAnalysis(namedtuple('PlayerAnalysis', [
  'id', 'titled', 'engine', 'gamesPlayed', 'closedReports', 'gameAnalyses',
  'PVAssessment', 'PVDrawAssessment', 'PVLosingAssessment', 'PVOverallAssessment',
  'overallAssessment'])): # id = userId, engine = (True | False | None)
  def setEngine(self, engine):
    return PlayerAnalysis(
      id = self.id,
      titled = self.titled, 
      engine = engine, 
      gamesPlayed = self.gamesPlayed,
      closedReports = self.closedReports,
      gameAnalyses = self.gameAnalyses,
      PVAssessment = self.PVAssessment,
      PVDrawAssessment = self.PVDrawAssessment,
      PVLosingAssessment = self.PVLosingAssessment,
      PVOverallAssessment = self.PVOverallAssessment,
      overallAssessment = self.overallAssessment)

  def tensorInputMoves(self):
    return self.gameAnalyses.tensorInputMoves()

  def tensorInputChunks(self):
    return self.gameAnalyses.tensorInputChunks()

  def tensorInputPVsDraw(self):
    return self.gameAnalyses.tensorInputPVsDraw()

  def tensorInputPVsLosing(self):
    return self.gameAnalyses.tensorInputPVsLosing()

  def tensorInputPVs(self):
    pvs = self.gameAnalyses.pv0ByAmbiguityStats()
    for i, pv in enumerate(pvs):
      if pv is None:
        pvs[i] = 0
    return pvs # should be a list of ints 5 items long

  def tensorInputOverallAssessment(self):
    if self.PVOverallAssessment is not None:
      return [int(self.anoaActivation()), int(self.PVOverallAssessment)]
    return None

  def tensorInputPVsOverall(self):
    pvs = [self.PVAssessment, self.PVDrawAssessment, self.PVLosingAssessment]
    if all(a is not None for a in pvs):
      return pvs
    return None

  def moveActivations(self):
    return self.gameAnalyses.moveActivations()

  def chunkActivations(self):
    return self.gameAnalyses.chunkActivations()

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

  def CSVPVsDrawish(self):
    return [int(self.engine)] + self.tensorInputPVsDraw()

  def CSVPVsLosing(self):
    return [int(self.engine)] + self.tensorInputPVsLosing()

  def CSVPVsOverall(self):
    if self.tensorInputPVsOverall() is not None:
      return [int(self.engine)] + self.tensorInputPVsOverall()
    return None

  def CSVOverallAssessment(self):
    if self.tensorInputOverallAssessment() is not None:
      return [int(self.engine)] + self.tensorInputOverallAssessment()
    return None

  def anoaActivation(self):
    anoa = sorted(self.gameAnalyses.assessmentNoOutlierAverages(), reverse=True)
    retained = anoa[:max(1, int(0.3*len(anoa)))]
    if len(retained) > 0:
      return numpy.mean(retained)
    return 0

  def report(self, thresholds):
    return {
      'userId': self.id,
      'isLegit': self.isLegit(thresholds),
      'activation': int(self.overallAssessment),
      'pv0ByAmbiguity': self.gameAnalyses.pv0ByAmbiguityStats(),
      'games': self.gameAnalyses.reportDicts()
    }

  def isLegit(self, thresholds):
    if self.overallAssessment is not None:
      gamesAnalysed = len(self.gameAnalyses.gameAnalyses)

      noOutlierAverages = self.gameAnalyses.assessmentNoOutlierAverages()

      moderateGames = sum([int(a > thresholds['averages']['moderate']) for a in noOutlierAverages])
      
      slightGames = sum([int(a > thresholds['averages']['slight']) for a in noOutlierAverages])
      susGames = sum([int(a > thresholds['averages']['suspicious']) for a in noOutlierAverages])
      verySusGames = sum([int(a > thresholds['averages']['verysuspicious']) for a in noOutlierAverages])
      exceptionalGames = sum([int(a > thresholds['averages']['exceptional']) for a in noOutlierAverages])

      legitGames = sum([int(a < thresholds['averages']['legit']) for a in noOutlierAverages])

      if not self.titled and self.overallAssessment > thresholds['overall']['engine'] and (
        (exceptionalGames >= (1/10)*gamesAnalysed and exceptionalGames > 0)
        or (verySusGames >= (1/10)*gamesAnalysed and verySusGames > 1)
        or (susGames >= (3/10)*gamesAnalysed and susGames > 2)
        or (slightGames >= (4/10)*gamesAnalysed and slightGames > 4)):
        return False
      elif self.overallAssessment < thresholds['overall']['legit'] and moderateGames == 0 and gamesAnalysed > 4:
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
      PVAssessment = bson.get('PVAssessment', None),
      PVDrawAssessment = bson.get('PVDrawAssessment', None),
      PVLosingAssessment = bson.get('PVLosingAssessment', None),
      PVOverallAssessment = bson.get('PVOverallAssessment', None),
      overallAssessment = bson.get('overallAssessment', None))

  @staticmethod
  def writes(playerAnalysis):
    return {
      '_id': playerAnalysis.id,
      'titled': playerAnalysis.titled,
      'engine': playerAnalysis.engine,
      'gamesPlayed': playerAnalysis.gamesPlayed,
      'closedReports': playerAnalysis.closedReports,
      'PVAssessment': playerAnalysis.PVAssessment,
      'PVDrawAssessment': playerAnalysis.PVDrawAssessment,
      'PVLosingAssessment': playerAnalysis.PVLosingAssessment,
      'PVOverallAssessment': playerAnalysis.PVOverallAssessment,
      'overallAssessment': playerAnalysis.overallAssessment,
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

  def write(self, playerAnalysis):
    self.playerAnalysisColl.update(
      {'_id': playerAnalysis.id},
      {'$set': PlayerAnalysisBSONHandler.writes(playerAnalysis)},
      upsert=True)
    self.gameAnalysisDB.lazyWriteGames(playerAnalysis.gameAnalyses)

  def lazyWriteMany(self, playerAnalyses):
    [self.write(playerAnalysis) for playerAnalysis in playerAnalyses]