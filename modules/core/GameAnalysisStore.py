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
    [self.games.append(g) for g in games if (not self.hasGameId(g.id) and g.emts is not None)]

  def addGameAnalyses(self, gameAnalyses):
    [self.gameAnalyses.append(ga) for ga in gameAnalyses if not self.gameIdHasAnalysis(ga.gameId)]

  def randomGamesWithoutAnalysis(self, size = 1):
    gWithout = self.gamesWithoutAnalysis()
    return [gWithout[x] for x in np.random.choice(list(range(len(gWithout))), min(len(gWithout), size), replace=False)]