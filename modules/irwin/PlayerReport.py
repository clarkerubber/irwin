from default_imports import *

import random

from datetime import datetime
from math import ceil

import numpy as np

from modules.game.AnalysedGame import AnalysedGame
from modules.game.Player import Player, PlayerID
from modules.auth.Auth import AuthID
from modules.irwin.AnalysedGameModel import AnalysedGamePrediction
from modules.irwin.GameReport import GameReport

PlayerReportID = NewType('PlayerReportID', str)

class PlayerReport(NamedTuple('PlayerReport', [
        ('id', PlayerReportID),
        ('userId', PlayerID),
        ('owner', AuthID),
        ('activation', int),
        ('gameReports', List[GameReport]),
        ('date', datetime)
    ])):
    @property
    def playerId(self):
        return self.userId

    @staticmethod
    def new(player: Player, gamesAndPredictions: Iterable[Tuple[AnalysedGame, AnalysedGamePrediction]], owner: AuthID = 'test'):
        reportId = PlayerReport.makeId()
        gamesAndPredictions = [(ag, agp) for ag, agp in gamesAndPredictions if agp is not None]
        gameReports = [GameReport.new(analysedGame, analysedGamePrediction, reportId) for analysedGame, analysedGamePrediction in gamesAndPredictions]
        return PlayerReport(
            id=reportId,
            userId=player.id,
            owner=owner,
            activation=PlayerReport.playerPrediction(player, [agp for _, agp in gamesAndPredictions]),
            gameReports=gameReports,
            date=datetime.now())

    @staticmethod
    def makeId() -> PlayerReportID:
        return str("%016x" % random.getrandbits(64))

    @staticmethod
    def playerPrediction(player: Player, analysedGamePredictions: List[AnalysedGamePrediction]) -> int:
        sortedGameActivations = sorted([gp.weightedGamePrediction() for gp in analysedGamePredictions], reverse=True)
        topGameActivations = sortedGameActivations[:ceil(0.15*len(sortedGameActivations))]
        topGameActivationsAvg = int(np.average(topGameActivations)) if len(topGameActivations) > 0 else 0

        aboveUpper = len([i for i in sortedGameActivations if i > 90])
        aboveLower = len([i for i in sortedGameActivations if i > 80])

        if aboveUpper > 2 and player.gamesPlayed < 500:
            result = topGameActivationsAvg
        elif aboveLower > 0:
            result = min(92, topGameActivationsAvg)
        else:
            result = min(62, topGameActivationsAvg)
        return result

    def reportDict(self) -> Dict:
        return {
            'userId': self.userId,
            'owner': self.owner,
            'activation': int(self.activation),
            'games': [gameReport.reportDict() for gameReport in self.gameReports]
        }