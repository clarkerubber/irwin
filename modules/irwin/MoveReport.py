from default_imports import *

from modules.game.AnalysedMove import AnalysedMove, TrueRank
from modules.irwin.AnalysedGameModel import WeightedMovePrediction

class MoveReport(NamedTuple('MoveReport', [
        ('activation', WeightedMovePrediction),
        ('rank', TrueRank),
        ('ambiguity', int),
        ('advantage', int),
        ('loss', int)
    ])):
    @staticmethod
    def new(analysedMove: AnalysedMove, movePrediction: WeightedMovePrediction):
        return MoveReport(
            activation=movePrediction,
            rank=analysedMove.trueRank(),
            ambiguity=analysedMove.ambiguity(),
            advantage=int(100*analysedMove.advantage()),
            loss=int(100*analysedMove.winningChancesLoss()))

    def reportDict(self):
        return {
            'a': self.activation,
            'r': self.rank,
            'm': self.ambiguity,
            'o': self.advantage,
            'l': self.loss
        }