from collections import namedtuple

GameAnalysisPlayerPivot = namedtuple('GameAnalysisPlayerPivot', ['id', 'userId', 'engine', 'length'])

class GameAnalysisPlayerPivotBSONHandler:
  @staticmethod
  def reads(bson):
    return GameAnalysisPlayerPivot(
      id = bson['_id'],
      userId = bson['userId'],
      engine = bson['engine'],
      length = bson['length'])

  @staticmethod
  def writes(GameAnalysisPlayerPivot):
    return {
      '_id': GameAnalysisPlayerPivot.id,
      'userId': GameAnalysisPlayerPivot.userId,
      'engine': GameAnalysisPlayerPivot.engine,
      'length': GameAnalysisPlayerPivot.length
    }

class GameAnalysisPlayerPivotDB(namedtuple('GameAnalysisPlayerPivotDB', ['GameAnalysisPlayerPivotColl'])):
  def byEngineAndLength(self, engine, length):
    return [GameAnalysisPlayerPivotBSONHandler.reads(bson) for bson in self.GameAnalysisPlayerPivotColl.find({'engine': engine, 'length': length})]