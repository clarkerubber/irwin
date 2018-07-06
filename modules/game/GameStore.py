from default_imports import *

from modules.game.Player import PlayerID
from modules.game.Game import Game, GameID, GameTensor, Emt
from modules.game.AnalysedGame import AnalysedGame, AnalysedGameTensor

import numpy as np
import math
import json

@validated
class GameStore(NamedTuple('GameStore', [
        ('playerId', PlayerID)
        ('games', List[Game]), 
        ('analysedGames', List[AnalysedGame])
    ])):
    @staticmethod
    @validated
    def new(playerId: PlayerID) -> GameStore:
        return GameStore(playerId, [], [])

    @validated
    def gamesWithoutAnalysis(self, excludeIds: List[GameID] = []) -> List[Game]:
        return [game for game in self.games if not self.gameIdHasAnalysis(game.id) if (game.id not in excludeIds)]

    @validated
    def gameIdHasAnalysis(self, gid: GameID) -> bool:
        return any([ga for ga in self.analysedGames if ga.gameId == gid])

    @validated
    def hasGameId(self, gid: GameID) -> bool:
        return any([g for g in self.games if gid == g.id])

    @validated
    def gameById(self, gid: GameID) -> Opt[Game]:
        return next(iter([g for g in self.games if gid == g.id]), None)

    @validated
    def addGames(self, games: List[Game]) -> None:
        [self.games.append(g) for g in games if (not self.hasGameId(g.id) and g.emts is not None and len(g.pgn) < 120 and len(g.pgn) > 40)]

    @validated
    def addAnalysedGame(self, ga: AnalysedGame) -> None:
        if not self.gameIdHasAnalysis(ga.gameId) and ga is not None and len(ga.analysedMoves) < 60 and len(ga.analysedMoves) > 20:
            self.analysedGames.append(ga)

    @validated
    def addAnalysedGames(self, analysedGames: List[AnalysedGame]) -> None:
        [self.addAnalysedGame(ga) for ga in analysedGames]

    @validated
    def randomGamesWithoutAnalysis(self, size: int = 10, excludeIds: List[GameID] = []) -> List[Game]:
        gWithout = self.gamesWithoutAnalysis(excludeIds)
        if len(gWithout) > 0:
            return [gWithout[x] for x in np.random.choice(list(range(len(gWithout))), min(len(gWithout), size), replace=False)]
        return []

    @validated
    def gameTensors(self) -> List[GameTensor]:
        tensors = [(g.id, g.tensor(self.playerId)) for g in self.games]
        return [t for t in tensors if t[1] is not None]

    @validated
    def gameTensorsWithoutAnalysis(self) -> List[GameTensor]:
        return [(gid, t) for gid, t in self.gameTensors(self.playerId) if not self.gameIdHasAnalysis(gid)]

    @validated
    def analysedGameTensors(self) -> List[AnalysedGameTensor]:
        return [(analysedGame.tensor(), analysedGame.length()) for analysedGame in self.analysedGames if len(analysedGame.analysedMoves) < 60 and len(analysedGame.analysedMoves) > 20 and analysedGame.emtAverage() < 2000]

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