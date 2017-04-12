from collections import namedtuple
from math import exp

class AnalysedMove(namedtuple('AnalysedMove', ['uci', 'move', 'analysis', 'emt'])):
  def inTopFive(self):
    return any(self.uci == am.uci for am in self.analysis)

  def isTop(self):
    return self.uci == self.top().uci

  def top(self):
    return next(iter(self.analysis or []), None)

  def bottom(self):
    return self.analysis[-1]

  def playedScore(self):
    return next((am.score for am in self.analysis if am.uci == self.uci), None)

  def winningChancesLoss(self):
    score = self.playedScore()
    if score is not None:
      return winningChances(self.top().score) - winningChances(score)
    else:
      return None

  def allAmbiguous(self):
    return similarChances(winningChances(self.top().score), winningChances(self.bottom().score))

Analysis = namedtuple('Analysis', ['uci', 'score'])
Score = namedtuple('Score', ['cp', 'mate'])

def winningChances(score):
  if score.mate is not None:
    return 1 if score.mate > 0 else -1
  else:
    return 2 / (1 + exp(-0.004 * score.cp)) - 1

def similarChances(c1, c2):
  return abs(c1 - c2) < 0.1

class AnalysedMoveBSONHandler:
  @staticmethod
  def reads(bson):
    return AnalysedMove(
      uci = bson['uci'],
      move = bson['move'],
      analysis = [Analysis(a['uci'], Score(a['score']['cp'], a['score']['mate'])) for a in bson['analysis']],
      emt = bson['emt'])

  @staticmethod
  def writes(analysedMove):
    return {
      'uci': analysedMove.uci,
      'move': analysedMove.move,
      'analysis': [{'uci': a.uci, 'score': {'cp': a.score.cp, 'mate': a.score.mate}} for a in analysedMove.analysis],
      'emt': analysedMove.emt
    }