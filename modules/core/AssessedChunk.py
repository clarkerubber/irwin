from collections import namedtuple
from modules.irwin.IrwinReport import IrwinReportBSONHandler

# For moves chunks (groups of 10) that have been assessed by Irwin/Tensorflow

AssessedChunk = namedtuple('AssessedChunk', ['move', 'irwinReport']) # move = move number

class AssessedChunkBSONHandler:
  @staticmethod
  def reads(bson):
    return AssessedChunk(
      move = bson['move'],
      irwinReport = IrwinReportBSONHandler.reads(bson['irwinReport'])
    )

  @staticmethod
  def writes(assessedChunk):
    return {
      'move': assessedChunk.move,
      'irwinReport': IrwinReportBSONHandler.writes(assessedChunk.irwinReport)
    }