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
      prediction = int(100*prediction))

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

  def byEngineLengthAndConfidence(self, engine, length, prediction):
    print("finding: "+str(engine)+" : "+str(length)+" : "+str(prediction))
    if engine:
      return [ConfidentGameAnalysisPivotBSONHandler.reads(bson) for bson in self.confidentGameAnalysisPivotColl.find({'engine': engine, 'length': length, 'prediction': {'$gte': prediction}})]
    return [ConfidentGameAnalysisPivotBSONHandler.reads(bson) for bson in self.confidentGameAnalysisPivotColl.find({'engine': engine, 'length': length, 'prediction': {'$lte': prediction}})]

  def writeMany(self, confidentGameAnalysisPivots):
    [self.confidentGameAnalysisPivotColl.insert_many([ConfidentGameAnalysisPivotBSONHandler.writes(cga) for cga in confidentGameAnalysisPivots])]

  def write(self, cga): # Game
    self.confidentGameAnalysisPivotColl.update_one({'_id': cga.id}, {'$set': ConfidentGameAnalysisPivotBSONHandler.writes(cga)}, upsert=True)

  def lazyWriteMany(self, cgas):
    [self.write(cga) for cga in cgas]