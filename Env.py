from pymongo import MongoClient

from chess import uci

from modules.fishnet.fishnet import stockfish_command

from modules.core.Game import GameDB
from modules.core.GameAnalysis import GameAnalysisDB
from modules.core.Player import PlayerDB

from modules.Api import Api

from modules.irwin.Irwin import Irwin
from modules.irwin.TrainingStats import TrainingStatsDB
from modules.irwin.FalseReports import FalseReportsDB

class Env:
  def __init__(self, settings):
    self.settings = settings

    self.engine = uci.popen_engine(stockfish_command(settings['stockfish']['update']))
    self.engine.setoption({'Threads': settings['stockfish']['threads'], 'Hash': settings['stockfish']['memory']})
    self.engine.uci()
    self.infoHandler = uci.InfoHandler()
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
    self.gameColl = self.db.game
    self.GameAnalysisColl = self.db.gameAnalysis

    self.trainingStatsColl = self.db.trainingStats
    self.falseReportsColl = self.db.falseReports

    # database abstraction
    self.playerDB = PlayerDB(self.playerColl)
    self.gameDB = GameDB(self.gameColl)
    self.gameAnalysisDB = GameAnalysisDB(self.GameAnalysisColl)

    self.trainingStatsDB = TrainingStatsDB(self.trainingStatsColl)
    self.falseReportsDB = FalseReportsDB(self.falseReportsColl)

    # Irwin
    self.irwin = Irwin(self, settings['irwin'])