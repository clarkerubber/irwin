from collections import namedtuple

from modules.core.PlayerAssessments import PlayerAssessments

# thin wrapper class for multiple games
class Games(namedtuple('Games', ['games'])):
  def byId(self, gameId):
    return next((g for g in self.games if g.id == gameId), None)

  def ids(self):
    return [g.id for g in self.games]

  def hasId(self, gameId):
    return (gameId in self.ids())