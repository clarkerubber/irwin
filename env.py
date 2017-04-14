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

class IrwinEnv:
  def __init__(self, settings):
    self.settings = settings

    self.engine = chess.uci.popen_engine(stockfish_command(False))
    self.engine.setoption({'Threads': settings.threads, 'Hash': settings.memory})
    self.engine.uci()
    self.infoHandler = chess.uci.InfoHandler()
    self.engine.info_handlers.append(self.infoHandler)

    self.api = Api(settings.token)

    # Set up mongodb
    self.client = MongoClient()
    self.db = self.client.irwin

    # Colls
    self.playerColl = self.db.player
    self.GameAnalysisColl = self.db.gameAnalysis
    self.gameColl = self.db.game
    self.playerAssessmentColl = self.db.playerAssessment
    self.playerAnalysisColl = self.db.playerAnalysis
    self.trainingStatsColl = self.db.trainingStats

    # database abstraction
    self.gameDB = GameDB(self.gameColl)
    self.playerAssessmentDB = PlayerAssessmentDB(self.playerAssessmentColl)
    self.gameAnalysisDB = GameAnalysisDB(self.GameAnalysisColl, self.gameDB, self.playerAssessmentDB)
    self.playerAnalysisDB = PlayerAnalysisDB(self.playerAnalysisColl, self.gameAnalysisDB)
    self.trainingStatsDB = TrainingStatsDB(self.trainingStatsColl)

    # Irwin
    self.irwin = Irwin(
      api = self.api,
      trainingStatsDB = self.trainingStatsDB,
      playerAnalysisDB = self.playerAnalysisDB
    )