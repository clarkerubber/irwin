import logging

from pymongo import MongoClient

from chess import uci

from modules.fishnet.fishnet import stockfish_command

from Api import Api

from modules.core.Game import GameDB
from modules.core.GameAnalysis import GameAnalysisDB
from modules.core.Player import PlayerDB
from modules.core.PositionAnalysis import PositionAnalysisDB

from modules.queue.BasicPlayerQueue import BasicPlayerQueueDB
from modules.queue.DeepPlayerQueue import DeepPlayerQueueDB

from modules.irwin.GameAnalysisActivation import GameAnalysisActivationDB
from modules.irwin.GameBasicActivation import GameBasicActivationDB

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
        self.gameAnalysisColl = self.db.gameAnalysis
        self.positionAnalysisColl = self.db.positionAnalysis

        self.basicPlayerQueueColl = self.db.basicPlayerQueue
        self.deepPlayerQueueColl = self.db.deepPlayerQueue

        self.gameAnalysisActivationColl = self.db.gameAnalysisActivation
        self.gameBasicActivationColl = self.db.gameBasicActivation

        # database abstraction
        self.playerDB = PlayerDB(self.playerColl)
        self.gameDB = GameDB(self.gameColl)
        self.gameAnalysisDB = GameAnalysisDB(self.gameAnalysisColl)
        self.positionAnalysisDB = PositionAnalysisDB(self.positionAnalysisColl)

        self.basicPlayerQueueDB = BasicPlayerQueueDB(self.basicPlayerQueueColl)
        self.deepPlayerQueueDB = DeepPlayerQueueDB(self.deepPlayerQueueColl)

        self.gameAnalysisActivationDB = GameAnalysisActivationDB(self.gameAnalysisActivationColl)
        self.gameBasicActivationDB = GameBasicActivationDB(self.gameBasicActivationColl)

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