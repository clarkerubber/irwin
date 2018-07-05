from collections import namedtuple
from pprint import pprint

from modules.game.AnalysedGame import AnalysedGame

import numpy as np
import math
import json

class GameStore(namedtuple('GameStore', ['games', 'analysedGames'])):
    def gamesWithoutAnalysis(self, excludeIds=[]):
        return [game for game in self.games if not self.gameIdHasAnalysis(game.id) if (game.id not in excludeIds)]

    def gameIdHasAnalysis(self, gid):
        return any([ga for ga in self.analysedGames if ga.gameId == gid])

    def hasGameId(self, gid):
        return any([g for g in self.games if gid == g.id])

    def gameById(self, gid):
        return next(iter([g for g in self.games if gid == g.id]), None)

    def addGames(self, games):
        [self.games.append(g) for g in games if (not self.hasGameId(g.id) and g.emts is not None and len(g.pgn) < 120 and len(g.pgn) > 40)]

    def addAnalysedGame(self, ga):
        if not self.gameIdHasAnalysis(ga.gameId) and ga is not None and len(ga.analysedMoves) < 60 and len(ga.analysedMoves) > 20:
            self.analysedGames.append(ga)

    def addAnalysedGames(self, analysedGames):
        [self.addAnalysedGame(ga) for ga in analysedGames]

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

    def analysedGameTensors(self):
        return [(analysedGame.analysedMoveTensors(), analysedGame.length()) for analysedGame in self.analysedGames if len(analysedGame.analysedMoves) < 60 and len(analysedGame.analysedMoves) > 20 and analysedGame.emtAverage() < 2000]

    def moveRankByTime(self):
        output = []
        [output.extend(ga.moveRankByTime()) for ga in self.analysedGames]
        return output

    def moveRankByTimeJSON(self):
        return json.dumps(self.moveRankByTime())

    def lossByTime(self):
        output = []
        [output.extend(ga.lossByTime()) for ga in self.analysedGames]
        return output

    def lossByTimeJSON(self):
        return json.dumps(self.lossByTime())

    def lossByRank(self):
        output = []
        [output.extend(ga.lossByRank()) for ga in self.analysedGames]
        return output

    def lossByRankJSON(self):
        return json.dumps(self.lossByRank())

    @staticmethod
    def new():
        return GameStore([], [])