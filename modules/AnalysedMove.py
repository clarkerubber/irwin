from collections import namedtuple

AnalysedMove = namedtuple('AnalysedMove', ['uci', 'move', 'analysis', 'emt'])

class AnalysedMoveBSONHandler:
  @staticmethod
  def reads(bson):
    return AnalysedMove(**bson)

  @staticmethod
  def writes(analysedMove):
    return analysedMove._asdict()