from collections import namedtuple
from pprint import pprint

class ConfidentGameAnalysisPivot(namedtuple('ConfidentGameAnalysis', ['id', 'userId', 'engine', 'length', 'prediction'])):
  @staticmethod
  def fromGamesAnalysisandPrediction(gameAnalysis, prediction, engine):
    return ConfidentGameAnalysisPivot(
      id = gameAnalysis.id,
      userId = gameAnalysis.userId,
      engine = engine,
      length = len(gameAnalysis.moveAnalyses),
      prediction = prediction)

class ConfidentGameAnalysisPivotBSONHandler:
  @staticmethod
  def reads(bson):
    return ConfidentGameAnalysisPivot(
      id = bson['_id'],
      userId = bson['userId'],
      engine = bson['engine'],
      length = bson['length'],
      prediction = bson['prediction'])

  @staticmethod
  def writes(cga):
    return {
      '_id': cga.id,
      'userId': cga.userId,
      'engine': cga.engine,
      'length': cga.length,
      'prediction': cga.prediction
    }

class ConfidentGameAnalysisPivotDB(namedtuple('ConfidentGameAnalysisPivotDB', ['confidentGameAnalysisPivotColl'])):
  def byEngineAndLength(self, engine, length):
    return [ConfidentGameAnalysisPivotBSONHandler.reads(bson) for bson in self.confidentGameAnalysisPivotColl.find({'engine': engine, 'length': length})]

  def byEngineAndPrediction(self, engine, prediction):
    if engine:
      return [ConfidentGameAnalysisPivotBSONHandler.reads(bson) for bson in self.confidentGameAnalysisPivotColl.find({'engine': engine, 'prediction': {'$gte': prediction}})]
    return [ConfidentGameAnalysisPivotBSONHandler.reads(bson) for bson in self.confidentGameAnalysisPivotColl.find({'engine': engine, 'prediction': {'$lte': prediction}})]

  def byEngineLengthAndPrediction(self, engine, length, prediction):
    if engine:
      return [ConfidentGameAnalysisPivotBSONHandler.reads(bson) for bson in self.confidentGameAnalysisPivotColl.find({'engine': engine, 'length': length, 'prediction': {'$gte': prediction}})]
    return [ConfidentGameAnalysisPivotBSONHandler.reads(bson) for bson in self.confidentGameAnalysisPivotColl.find({'engine': engine, 'length': length, 'prediction': {'$lte': prediction}})]

  def byPredictionRangeAndLength(self, minPred, maxPred, length):
    return [ConfidentGameAnalysisPivotBSONHandler.reads(bson) for bson in self.confidentGameAnalysisPivotColl.find({'prediction': {'$gte': minPred, '$lte': maxPred}})]

  def writeMany(self, confidentGameAnalysisPivots):
    [self.confidentGameAnalysisPivotColl.insert_many([ConfidentGameAnalysisPivotBSONHandler.writes(cga) for cga in confidentGameAnalysisPivots])]

  def write(self, cga): # Game
    self.confidentGameAnalysisPivotColl.update_one({'_id': cga.id}, {'$set': ConfidentGameAnalysisPivotBSONHandler.writes(cga)}, upsert=True)

  def lazyWriteMany(self, cgas):
    [self.write(cga) for cga in cgas]