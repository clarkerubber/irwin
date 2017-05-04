from collections import namedtuple
from modules.core.PlayerAssessment import nullPlayerAssessment

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

  def addNulls(self, userId, games, gameJSONs): # Add practically blank playerAssessment objects for games that don't have one
    new = self.playerAssessments
    for game in games:
      gameJSON = gameJSONs.get(game.id, None)
      if gameJSON is not None and not self.hasGameId(game.id):
        new.append(nullPlayerAssessment(game.id, userId, game.color == "white"))
    return PlayerAssessments(new)