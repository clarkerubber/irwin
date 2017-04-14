from collections import namedtuple

import datetime

class PlayerAnalysis(namedtuple('PlayerAnalysis', ['id', 'engine', 'gameAnalyses'])): # id = userId, engine = (True | False | None)
  def setEngine(self, engine):
    return PlayerAnalysis(self.id, engine, self.gameAnalyses)

class PlayerAnalysisBSONHandler:
  @staticmethod
  def reads(bson, gameAnalyses):
    return PlayerAnalysis(
      id = bson['_id'],
      engine = bson['engine'],
      gameAnalyses = gameAnalyses)

  def writes(playerAnalysis):
    return {
      '_id': playerAnalysis.id,
      'engine': playerAnalysis.engine,
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

  def unsorted(self): # Players who have not been marked as Engine or Legit
    return [self.byId(p['_id']) for p in self.playerAnalysisColl.find({'engine': None})]

  def write(self, playerAnalysis):
    self.playerAnalysisColl.update(
      {'_id': playerAnalysis.id},
      {'$set': PlayerAnalysisBSONHandler.writes(playerAnalysis)},
      upsert=True)

  def lazyWriteMany(self, playerAnalyses):
    [self.write(playerAnalysis) for playerAnalysis in playerAnalyses]