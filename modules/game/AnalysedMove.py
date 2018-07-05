from collections import namedtuple
from functools import lru_cache
from math import exp
import numpy as np

# For moves that have been analysed by stockfish

Analysis = namedtuple('Analysis', ['uci', 'engineEval'])

class EngineEval(namedtuple('EngineEval', ['cp', 'mate'])):
    def inverse(self):
        return EngineEval(-self.cp if self.cp is not None else None,
            -self.mate if self.mate is not None else None)

class AnalysedMove(namedtuple('AnalysedMove', ['uci', 'move', 'emt', 'blur', 'engineEval', 'analyses'])):
    def tensor(self, timeAvg, wclAvg):
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
    def nullTensor():
        return 10*[0]

    def top(self):
        return next(iter(self.analyses or []), None)

    def difToNextBest(self):
        tr = self.trueRank()
        if tr is not None and tr != 1:
            return winningChances(self.analyses[tr-2].engineEval) - self.advantage()
        elif tr == 1:
            return 0
        else:
            return winningChances(self.analyses[-1].engineEval) - self.advantage()

    def difToNextWorst(self):
        tr = self.trueRank()
        if tr is not None and tr <= len(self.analyses)-1:
            return winningChances(self.analyses[tr].engineEval) - self.advantage()
        return 0

    def PVsWinningChancesLoss(self):
        return [winningChances(self.top().engineEval) - winningChances(a.engineEval) for a in self.analyses]

    def averageWinningChancesLoss(self):
        return np.average(self.PVsWinningChancesLoss())

    def winningChancesLoss(self, usePV=False):
        adv = self.advantage()
        if usePV:
            r = self.trueRank()
            if r is not None:
                adv = winningChances(self.analyses[r-1].engineEval)
                
        return max(0, winningChances(self.top().engineEval) - adv)

    def advantage(self):
        return winningChances(self.engineEval)

    def ambiguity(self): # 1 = only one top move, 5 = all moves good
        return sum(int(similarChances(winningChances(self.top().engineEval), winningChances(analysis.engineEval))) for analysis in self.analyses)

    def trueRank(self):
        return next((x+1 for x, am in enumerate(self.analyses) if am.uci == self.uci), None)

    def rank(self):
        return min(15, next((x for x, am in enumerate(self.analyses) if am.uci == self.uci), self.projectedRank()) + 1)

    def projectedRank(self):
        if len(self.analyses) == 1:
            return 10
        else: # rise over run prediction of move rank given the difference between the winning chances in the bottom two analysed moves
            try:
                return len(self.analyses) + int(len(self.analyses)*abs(winningChances(self.analyses[-1].engineEval) - winningChances(self.engineEval)) / abs(winningChances(self.analyses[0].engineEval) - winningChances(self.analyses[-2].engineEval)))
            except ZeroDivisionError:
                return 10

@lru_cache(maxsize=64)
def winningChances(engineEval):
    if engineEval.mate is not None:
        return 1 if engineEval.mate > 0 else 0
    else:
        return 1 / (1 + exp(-0.004 * engineEval.cp))

def similarChances(c1, c2):
    return abs(c1 - c2) < 0.05

class AnalysisBSONHandler:
    @staticmethod
    def reads(bson):
        return Analysis(bson['uci'], EngineEvalBSONHandler.reads(bson['engineEval']))

    @staticmethod
    def writes(analysis):
        return {
            'uci': analysis.uci,
            'engineEval': EngineEvalBSONHandler.writes(analysis.engineEval)
        }

class EngineEvalBSONHandler:
    @staticmethod
    def reads(bson):
        return EngineEval(**bson)

    def writes(engineEval):
        return engineEval._asdict()

class AnalysedMoveBSONHandler:
    @staticmethod
    def reads(bson):
        return AnalysedMove(
            uci = bson['uci'],
            move = bson['move'],
            emt = bson['emt'],
            blur = bson.get('blur', False),
            engineEval = EngineEvalBSONHandler.reads(bson['engineEval']),
            analyses = [AnalysisBSONHandler.reads(a) for a in bson['analyses']]
            )

    @staticmethod
    def writes(analysedMove):
        return {
            'uci': analysedMove.uci,
            'move': analysedMove.move,
            'emt': analysedMove.emt,
            'blur': analysedMove.blur,
            'engineEval': EngineEvalBSONHandler.writes(analysedMove.engineEval),
            'analyses': [AnalysisBSONHandler.writes(a) for a in analysedMove.analyses]
        }
