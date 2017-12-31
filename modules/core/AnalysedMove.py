from collections import namedtuple
from math import exp
import numpy as np

# For moves that have been analysed by stockfish

Analysis = namedtuple('Analysis', ['uci', 'score'])
Score = namedtuple('Score', ['cp', 'mate'])

class AnalysedMove(namedtuple('AnalysedMove', ['uci', 'move', 'emt', 'blur', 'score', 'analyses'])):
  def tensor(self, moveNumber, timeAvg, wclAvg):
    return [self.analysesWinningChances() + self.analysesWinningChanceLosses(), [
      self.emt - timeAvg,
      abs(self.emt - timeAvg) / (timeAvg + 1e-8),
      self.emt,
      float(self.blur),
      self.difToNextBest(),
      self.winningChancesLoss(),
      wclAvg,
      wclAvg - self.winningChancesLoss()], moveNumber, self.rank() + 1, int(40*self.advantage())+1, self.ambiguity()+1]

  def analysesWinningChances(self):
    c = [winningChances(a.score) for a in self.analyses]
    c += [0] * (5 - len(c))
    return c

  def analysesWinningChanceLosses(self):
    return [winningChances(self.top().score) - a for a in self.analysesWinningChances()]

  def top(self):
    return next(iter(self.analyses or []), None)

  def difToNextBest(self):
    tr = self.trueRank()
    if tr is not None and tr != 1:
      return winningChances(self.analyses[tr-2].score) - self.advantage()
    elif tr == 1:
      return 0
    else:
      return winningChances(self.analyses[-1].score) - self.advantage()

  def winningChancesLoss(self):
    return max(0, winningChances(self.top().score) - self.advantage())

  def advantage(self):
    return winningChances(self.score)

  def ambiguous(self): # if the top and second moves both have similar winning chances, the position is ambiguous
    try:
      return similarChances(winningChances(self.top().score), winningChances(self.analyses[1].score))
    except IndexError:
      return False

  def ambiguity(self): # 1 = only one top move, 5 = all moves good
    return sum(int(similarChances(winningChances(self.top().score), winningChances(analysis.score))) for analysis in self.analyses)

  def trueRank(self):
    return next((x+1 for x, am in enumerate(self.analyses) if am.uci == self.uci), None)

  def rank(self):
    return min(15, next((x for x, am in enumerate(self.analyses) if am.uci == self.uci), self.projectedRank()) + 1)

  def projectedRank(self):
    if len(self.analyses) == 1:
      return 10
    else: # rise over run prediction of move rank given the difference between the winning chances in the bottom two analysed moves
      try:
        return len(self.analyses) + int(len(self.analyses)*abs(winningChances(self.analyses[-1].score) - winningChances(self.score)) / abs(winningChances(self.analyses[0].score) - winningChances(self.analyses[-2].score)))
      except ZeroDivisionError:
        return 10

def winningChances(score):
  if score.mate is not None:
    return 1 if score.mate > 0 else 0
  else:
    return 1 / (1 + exp(-0.004 * score.cp))

def similarChances(c1, c2):
  return abs(c1 - c2) < 0.05

class AnalysisBSONHandler:
  @staticmethod
  def reads(bson):
    return Analysis(bson['uci'], ScoreBSONHandler.reads(bson['score']))

  @staticmethod
  def writes(analysis):
    return {
      'uci': analysis.uci,
      'score': ScoreBSONHandler.writes(analysis.score)
    }

class ScoreBSONHandler:
  @staticmethod
  def reads(bson):
    return Score(**bson)

  def writes(score):
    return score._asdict()

class AnalysedMoveBSONHandler:
  @staticmethod
  def reads(bson):
    return AnalysedMove(
      uci = bson['uci'],
      move = bson['move'],
      emt = bson['emt'],
      blur = bson.get('blur', False),
      score = ScoreBSONHandler.reads(bson['score']),
      analyses = [AnalysisBSONHandler.reads(a) for a in bson['analyses']]
      )

  @staticmethod
  def writes(analysedMove):
    return {
      'uci': analysedMove.uci,
      'move': analysedMove.move,
      'emt': analysedMove.emt,
      'blur': analysedMove.blur,
      'score': ScoreBSONHandler.writes(analysedMove.score),
      'analyses': [AnalysisBSONHandler.writes(a) for a in analysedMove.analyses]
    }
