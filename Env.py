from pymongo import MongoClient

import chess
import chess.uci
from modules.fishnet.fishnet import stockfish_command

from modules.core.Game import GameDB
from modules.core.PlayerAssessment import PlayerAssessmentDB
from modules.core.GameAnalysis import GameAnalysisDB
from modules.core.PlayerAnalysis import PlayerAnalysisDB

from modules.Api import Api

from modules.irwin.Irwin import Irwin
from modules.irwin.TrainingStats import TrainingStatsDB
from modules.irwin.FalsePositives import FalsePositivesDB

class Env:
  def __init__(self, settings):
    self.settings = settings

    self.engine = chess.uci.popen_engine(stockfish_command(settings['stockfish']['update']))
    self.engine.setoption({'Threads': settings['stockfish']['threads'], 'Hash': settings['stockfish']['memory']})
    self.engine.uci()
    self.infoHandler = chess.uci.InfoHandler()
    self.engine.info_handlers.append(self.infoHandler)

    self.api = Api(settings['api']['url'], settings['api']['token'])

    # Set up mongodb
    self.client = MongoClient(settings['db']['host'])
    self.db = self.client.irwin
    if settings['db']['authenticate']:
      self.db.authenticate(
        settings['db']['authentication']['username'],
        settings['db']['authentication']['password'], mechanism='MONGODB-CR')

    # Colls
    self.playerColl = self.db.player
    self.GameAnalysisColl = self.db.gameAnalysis
    self.gameColl = self.db.game
    self.playerAssessmentColl = self.db.playerAssessment
    self.playerAnalysisColl = self.db.playerAnalysis
    self.trainingStatsColl = self.db.trainingStats
    self.falseReportsColl = self.db.falseReports

    # database abstraction
    self.gameDB = GameDB(self.gameColl)
    self.playerAssessmentDB = PlayerAssessmentDB(self.playerAssessmentColl)
    self.gameAnalysisDB = GameAnalysisDB(self.GameAnalysisColl, self.gameDB, self.playerAssessmentDB)
    self.playerAnalysisDB = PlayerAnalysisDB(self.playerAnalysisColl, self.gameAnalysisDB)
    self.trainingStatsDB = TrainingStatsDB(self.trainingStatsColl)
    self.falseReportsDB = FalseReportsDB(self.falseReportsColl)

    # Irwin
    self.irwin = Irwin(
      api = self.api,
      learner = settings['irwin']['learn'],
      trainingStatsDB = self.trainingStatsDB,
      playerAnalysisDB = self.playerAnalysisDB,
      falseReportsDB = self.falseReportsDB,
      settings = settings['irwin']
    )