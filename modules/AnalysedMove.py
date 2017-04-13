from collections import namedtuple
from math import exp

# For moves that have been analysed by stockfish

Analysis = namedtuple('Analysis', ['uci', 'score'])
Score = namedtuple('Score', ['cp', 'mate'])

class AnalysedMove(namedtuple('AnalysedMove', ['uci', 'move', 'emt', 'score', 'analyses'])):
  def inTopFive(self):
    return any(self.uci == am.uci for am in self.analyses)

  def isTop(self):
    return self.uci == self.top().uci

  def top(self):
    return next(iter(self.analyses or []), None)

  def bottom(self):
    return self.analyses[-1]

  def winningChancesLoss(self):
    return winningChances(self.top().score) - winningChances(self.score)

  def allAmbiguous(self):
    return similarChances(winningChances(self.top().score), winningChances(self.bottom().score))

def winningChances(score):
  if score.mate is not None:
    return 1 if score.mate > 0 else -1
  else:
    return 2 / (1 + exp(-0.004 * score.cp)) - 1

def similarChances(c1, c2):
  return abs(c1 - c2) < 0.1

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
      score = ScoreBSONHandler.reads(bson['score']),
      analyses = [AnalysisBSONHandler.reads(a) for a in bson['analyses']]
      )

  @staticmethod
  def writes(analysedMove):
    return {
      'uci': analysedMove.uci,
      'move': analysedMove.move,
      'emt': analysedMove.emt,
      'score': ScoreBSONHandler.writes(analysedMove.score),
      'analyses': [AnalysisBSONHandler.writes(a) for a in analysedMove.analyses]
    }