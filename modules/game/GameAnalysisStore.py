from collections import namedtuple
from pprint import pprint

from modules.game.GameAnalysis import GameAnalysis

import numpy as np
import math

class GameAnalysisStore(namedtuple('GameAnalysisStore', ['games', 'gameAnalyses'])):
    def gamesWithoutAnalysis(self, excludeIds=[]):
        return [game for game in self.games if not self.gameIdHasAnalysis(game.id) if (game.id not in excludeIds)]

    def gameIdHasAnalysis(self, gid):
        return any([ga for ga in self.gameAnalyses if ga.gameId == gid])

    def hasGameId(self, gid):
        return any([g for g in self.games if gid == g.id])

    def gameById(self, gid):
        return next(iter([g for g in self.games if gid == g.id]), None)

    def addGames(self, games):
        [self.games.append(g) for g in games if (not self.hasGameId(g.id) and g.emts is not None and len(g.pgn) < 120 and len(g.pgn) > 40)]

    def addGameAnalysis(self, ga):
        if not self.gameIdHasAnalysis(ga.gameId) and ga is not None and len(ga.moveAnalyses) < 60 and len(ga.moveAnalyses) > 20:
            self.gameAnalyses.append(gameAnalysis)

    def addGameAnalyses(self, gameAnalyses):
        [self.addGameAnalysis(ga) for ga in gameAnalyses]

    def randomGamesWithoutAnalysis(self, size = 10, excludeIds=[]):
        gWithout = self.gamesWithoutAnalysis(excludeIds)
        if len(gWithout) > 0:
            return [gWithout[x] for x in np.random.choice(list(range(len(gWithout))), min(len(gWithout), size), replace=False)]
        return []

    def gameTensors(self, userId):
        tensors = [(g.id, g.tensor(userId)) for g in self.games]
        return [t for t in tensors if t[1] is not None]

    def gameTensorsWithoutAnalysis(self, userId):
        return [(gid, t) for gid, t in self.gameTensors(userId) if not self.gameIdHasAnalysis(gid)]

    def gameAnalysisTensors(self):
        return [(gameAnalysis.moveAnalysisTensors(), gameAnalysis.length()) for gameAnalysis in self.gameAnalyses if len(gameAnalysis.moveAnalyses) < 60 and len(gameAnalysis.moveAnalyses) > 20 and gameAnalysis.emtAverage() < 2000]

    @staticmethod
    def new():
        return GameAnalysisStore([], [])