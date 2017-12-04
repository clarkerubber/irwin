from collections import namedtuple
import numpy as np
from pprint import pprint

class GameAnalysisStore(namedtuple('GameAnalysisStore', ['games', 'gameAnalyses'])):
  def gamesWithoutAnalysis(self):
    return [game for game in self.games if not self.gameIdHasAnalysis(game.id)]

  def gameIdHasAnalysis(self, gid):
    return any([ga for ga in self.gameAnalyses if ga.gameId == gid])

  def hasGameId(self, gid):
    return any([g for g in self.games if gid == g.id])

  def addGames(self, games):
    [self.games.append(g) for g in games if (not self.hasGameId(g.id) and g.emts is not None and len(g.pgn) < 120 and len(g.pgn) > 40)]

  def addGameAnalyses(self, gameAnalyses):
    [self.gameAnalyses.append(ga) for ga in gameAnalyses if not self.gameIdHasAnalysis(ga.gameId) and ga is not None and len(ga.moveAnalyses) < 60 and len(ga.moveAnalyses) > 20]

  def randomGamesWithoutAnalysis(self, size = 10):
    gWithout = self.gamesWithoutAnalysis()
    if len(gWithout) > 0:
      return [gWithout[x] for x in np.random.choice(list(range(len(gWithout))), min(len(gWithout), size), replace=False)]
    return []

  def gameAnalysisTensors(self):
    return [gameAnalysis.moveAnalysisTensors() for gameAnalysis in self.gameAnalyses if len(gameAnalysis.moveAnalyses) < 60 and len(gameAnalysis.moveAnalyses) > 20]

  @staticmethod
  def new():
    return GameAnalysisStore([], [])