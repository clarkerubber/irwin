from default_imports import *

from modules.game.EngineEval import EngineEval, EngineEvalBSONHandler

from modules.game.Game import Emt
from functools import lru_cache
from math import exp
import numpy as np

# For moves that have been analysed by stockfish

UCI = NewType('UCI', str)

MoveNumber = NewType('MoveNumber', int)

Analysis = NamedTuple('Analysis', [
    ('uci', 'UCI'),
    ('engineEval', 'EngineEval')
])

Rank = NewType('Rank', int)
TrueRank = NewType('TrueRank', Opt[Rank])

class AnalysedMove(NamedTuple('AnalysedMove', [
        ('uci', UCI),
        ('move', MoveNumber),
        ('emt', Emt),
        ('blur', bool),
        ('engineEval', EngineEval),
        ('analyses', List[Analysis])
    ])):
    def tensor(self, timeAvg: Number, wclAvg: Number) -> List[Number]:
        return [
            self.rank() + 1,
            self.ambiguity() + 1,
            self.advantage(),
            self.emt / (timeAvg + 1e-8), # elapsed move time / average
            abs(self.emt - timeAvg) / (timeAvg + 1e-8), # variance from average
            self.difToNextBest(),
            self.difToNextWorst(),
            self.winningChancesLoss(), # loss of advantage
            self.winningChancesLoss() - wclAvg, # loss in comparison to average
            self.averageWinningChancesLoss()
        ]

    @staticmethod
    def nullTensor() -> List[int]:
        return 10*[0]

    def top(self) -> Opt[Analysis]:
        return next(iter(self.analyses or []), None)

    def difToNextBest(self) -> Number:
        tr = self.trueRank()
        if tr is not None and tr != 1:
            return winningChances(self.analyses[tr-2].engineEval) - self.advantage()
        elif tr == 1:
            return 0
        else:
            return winningChances(self.analyses[-1].engineEval) - self.advantage()

    def difToNextWorst(self) -> Number:
        tr = self.trueRank()
        if tr is not None and tr <= len(self.analyses)-1:
            return winningChances(self.analyses[tr].engineEval) - self.advantage()
        return 0

    def PVsWinningChancesLoss(self) -> Number:
        return [winningChances(self.top().engineEval) - winningChances(a.engineEval) for a in self.analyses]

    def averageWinningChancesLoss(self) -> Number:
        return np.average(self.PVsWinningChancesLoss())

    def winningChancesLoss(self, usePV: bool = False) -> Number:
        adv = self.advantage()
        if usePV:
            r = self.trueRank()
            if r is not None:
                adv = winningChances(self.analyses[r-1].engineEval)
                
        return max(0, winningChances(self.top().engineEval) - adv)

    def advantage(self) -> Number:
        return winningChances(self.engineEval)

    def ambiguity(self) -> int: # 1 = only one top move, 5 = all moves good
        return sum(int(similarChances(winningChances(self.top().engineEval), winningChances(analysis.engineEval))) for analysis in self.analyses)

    def trueRank(self) -> TrueRank:
        return next((x+1 for x, am in enumerate(self.analyses) if am.uci == self.uci), None)

    def rank(self) -> Rank:
        return min(15, next((x for x, am in enumerate(self.analyses) if am.uci == self.uci), self.projectedRank()) + 1)

    def projectedRank(self) -> Number:
        if len(self.analyses) == 1:
            return 10
        else: # rise over run prediction of move rank given the difference between the winning chances in the bottom two analysed moves
            try:
                return len(self.analyses) + int(len(self.analyses)*abs(winningChances(self.analyses[-1].engineEval) - winningChances(self.engineEval)) / abs(winningChances(self.analyses[0].engineEval) - winningChances(self.analyses[-2].engineEval)))
            except ZeroDivisionError:
                return 10

@lru_cache(maxsize=64)
def winningChances(engineEval: EngineEval) -> Number:
    if engineEval.mate is not None:
        return 1 if engineEval.mate > 0 else 0
    else:
        return 1 / (1 + exp(-0.004 * engineEval.cp))

def similarChances(c1: Number, c2: Number) -> bool:
    return abs(c1 - c2) < 0.05

class AnalysisBSONHandler:
    @staticmethod
    def reads(bson: Dict) -> Analysis:
        return Analysis(bson['uci'], EngineEvalBSONHandler.reads(bson['engineEval']))

    @staticmethod
    def writes(analysis: Analysis) -> Dict:
        return {
            'uci': analysis.uci,
            'engineEval': EngineEvalBSONHandler.writes(analysis.engineEval)
        }


class AnalysedMoveBSONHandler:
    @staticmethod
    def reads(bson: Dict) -> AnalysedMove:
        return AnalysedMove(
            uci = bson['uci'],
            move = bson['move'],
            emt = bson['emt'],
            blur = bson.get('blur', False),
            engineEval = EngineEvalBSONHandler.reads(bson['engineEval']),
            analyses = [AnalysisBSONHandler.reads(a) for a in bson['analyses']]
            )

    @staticmethod
    def writes(analysedMove: AnalysedMove) -> Dict:
        return {
            'uci': analysedMove.uci,
            'move': analysedMove.move,
            'emt': analysedMove.emt,
            'blur': analysedMove.blur,
            'engineEval': EngineEvalBSONHandler.writes(analysedMove.engineEval),
            'analyses': [AnalysisBSONHandler.writes(a) for a in analysedMove.analyses]
        }
