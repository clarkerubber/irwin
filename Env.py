import logging

from pymongo import MongoClient

from chess import uci

from modules.fishnet.fishnet import stockfish_command

from modules.lichess.Api import Api

from modules.game.Game import GameDB
from modules.game.AnalysedGame import AnalysedGameDB
from modules.game.Player import PlayerDB
from modules.game.AnalysedPosition import AnalysedPositionDB

from modules.queue.BasicPlayerQueue import BasicPlayerQueueDB
from modules.queue.DeepPlayerQueue import DeepPlayerQueueDB
from modules.queue.ModReport import ModReportDB

from modules.irwin.AnalysedGameActivation import AnalysedGameActivationDB
from modules.irwin.GameBasicActivation import GameBasicActivationDB

from modules.irwin.AnalysisReport import PlayerReportDB, GameReportDB

from modules.irwin.Irwin import Irwin

class Env:
    def __init__(self, settings, engine=True):
        self.settings = settings
        self.engine = engine

        if self.engine:
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
        self.analysedGameColl = self.db.analysedGame
        self.analysedPositionColl = self.db.analysedPosition

        self.basicPlayerQueueColl = self.db.basicPlayerQueue
        self.deepPlayerQueueColl = self.db.deepPlayerQueue
        self.reportColl = self.db.report

        self.analysedGameActivationColl = self.db.analysedGameActivation
        self.gameBasicActivationColl = self.db.gameBasicActivation

        self.playerReportColl = self.db.playerReport
        self.gameReportColl = self.db.gameReport

        # database abstraction
        self.playerDB = PlayerDB(self.playerColl)
        self.gameDB = GameDB(self.gameColl)
        self.analysedGameDB = AnalysedGameDB(self.analysedGameColl)
        self.analysedPositionDB = AnalysedPositionDB(self.analysedPositionColl)

        self.basicPlayerQueueDB = BasicPlayerQueueDB(self.basicPlayerQueueColl)
        self.deepPlayerQueueDB = DeepPlayerQueueDB(self.deepPlayerQueueColl)
        self.modReportDB = ModReportDB(self.reportColl)

        self.analysedGameActivationDB = AnalysedGameActivationDB(self.analysedGameActivationColl)
        self.gameBasicActivationDB = GameBasicActivationDB(self.gameBasicActivationColl)

        self.playerReportDB = PlayerReportDB(self.playerReportColl)
        self.gameReportDB = GameReportDB(self.gameReportColl)

        # Irwin
        self.irwin = Irwin(self)

    def restartEngine(self):
        if self.engine:
            self.engine.kill()
            self.engine = uci.popen_engine(stockfish_command(self.settings['stockfish']['update']))
            self.engine.setoption({'Threads': self.settings['stockfish']['threads'], 'Hash': self.settings['stockfish']['memory']})
            self.engine.uci()
            self.infoHandler = uci.InfoHandler()
            self.engine.info_handlers.append(self.infoHandler)

    def __del__(self):
        logging.warning("Removing Env")
        self.engine.kill()
        try:
            del self.irwin
        except TypeError:
            pass