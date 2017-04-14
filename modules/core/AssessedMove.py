from collections import namedtuple
from modules.core.AnalysedMove import AnalysedMoveBSONHandler
from modules.core.IrwinReport import IrwinReportBSONHandler

# For moves that have been assessed by Irwin/Tensorflow

AssessedMove = namedtuple('AssessedMove', ['analysedMove', 'irwinReport'])

class AssessedMoveBSONHandler:
  @staticmethod
  def reads(bson):
    return AssessedMove(
      analysedMove = AnalysedMoveBSONHandler.reads(bson['analysedMove']),
      irwinReport = IrwinReportBSONHandler.reads(bson['irwinReport'])
    )

  @staticmethod
  def writes(assessedMove):
    return {
      'analysedMove': AnalysedMoveBSONHandler.writes(assessedMove.analysedMove),
      'irwinReport': IrwinReportBSONHandler.writes(assessedMove.irwinReport)
    }