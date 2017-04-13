from collections import namedtuple

class PlayerAssessments(namedtuple('PlayerAssessments', ['playerAssessments'])):
  def gameIds(self):
    return list([pa.gameId for pa in self.playerAssessments])

  def hasGameId(self, gameId):
    return any(gameId == pa.gameId for pa in self.playerAssessments)

  def byGameIds(self, gameIds):
    return [p for p in self.playerAssessments if p.gameId in gameIds]

  def byGameId(self, gameId):
    return next((p for p in self.playerAssessments if p.gameId == gameId), None)

  def suspicious(self):
    return [p for p in self.list if p.assessment > 2]