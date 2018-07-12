from default_imports import *

from modules.irwin.AnalysedGameModel import AnalysedGamePrediction, WeightedGamePrediction

from modules.irwin.MoveReport import MoveReport

from modules.game.AnalysedGame import AnalysedGame, AnalysedGameID
from modules.game.Player import PlayerID
from modules.game.Game import GameID

GameReportID = NewType('GameReportID', str)

class GameReport(NamedTuple('GameReport', [
        ('id', GameReportID),
        ('reportId', str),
        ('gameId', AnalysedGameID),
        ('activation', WeightedGamePrediction),
        ('moves', List[MoveReport])
    ])):
    @staticmethod
    def new(analysedGame: AnalysedGame, analysedGamePrediction: AnalysedGamePrediction, playerReportId: str):
        gameId = analysedGame.gameId
        return GameReport(
            id=GameReport.makeId(gameId, playerReportId),
            reportId=playerReportId,
            gameId=gameId,
            activation=analysedGamePrediction.weightedGamePrediction(),
            moves=[MoveReport.new(am, p) for am, p in zip(analysedGame.analysedMoves, analysedGamePrediction.weightedMovePredictions())])

    @staticmethod
    def makeId(gameId: GameID, reportId: str) -> GameReportID:
        return '{}/{}'.format(gameId, reportId)

    def reportDict(self):
        return {
            'gameId': self.gameId,
            'activation': self.activation,
            'moves': [move.reportDict() for move in self.moves]
        }