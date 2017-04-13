from collections import namedtuple
from modules.IrwinReport import IrwinReportBSONHandler

import datetime

PlayerAnalysis = namedtuple('PlayerAnalysis', ['userId', 'engine', 'gameAnalyses', 'irwinReport'])

class PlayerAnalysisBSONHandler:
  @staticmethod
  def reads(bson, gameAnalyses):
    return PlayerAnalysis(
      id = bson['_id'],
      engine = bson['engine'],
      gameAnalyses = gameAnalyses,
      irwinReport = IrwinReportBSONHandler.reads(bson['irwinReport']))

  def writes(playerAnalysis):
    return {
      '_id': playerAnalysis.id,
      'engine': playerAnalysis.engine,
      'irwinReport': IrwinReportBSONHandler.writes(playerAnalysis.irwinReport),
      'date': datetime.datetime.utcnow()
    }

class PlayerAnalysisDB:
  def __init__(self, playerAnalysisColl, gameAnalysisDB):
    self.playerAnalysisColl = playerAnalysisColl
    self.gameAnalysisDB = gameAnalysisDB