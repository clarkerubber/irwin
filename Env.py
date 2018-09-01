import logging

from pymongo import MongoClient

from chess import uci

from modules.fishnet.fishnet import stockfish_command

from modules.lichess.Api import Api

from modules.game.Game import GameDB
from modules.game.AnalysedGame import AnalysedGameDB
from modules.game.Player import PlayerDB
from modules.game.AnalysedPosition import AnalysedPositionDB

from modules.queue.IrwinQueue import IrwinQueueDB
from modules.queue.EngineQueue import EngineQueueDB

from modules.irwin.AnalysedGameActivation import AnalysedGameActivationDB
from modules.irwin.BasicGameActivation import BasicGameActivationDB

from modules.irwin.AnalysisReport import PlayerReportDB, GameReportDB

from modules.irwin.Env import Env as IrwinEnv
from modules.irwin.Irwin import Irwin

class Env:
    def __init__(self, config, engine=True, newmodel: bool = False):
        logging.debug('newmodel')
        logging.debug(newmodel)
        self.config = config
        self.engine = engine

        if self.engine:
            self.engine = uci.popen_engine(stockfish_command(config['stockfish']['update']))
            self.engine.setoption({'Threads': config['stockfish']['threads'], 'Hash': config['stockfish']['memory']})
            self.engine.uci()
            self.infoHandler = uci.InfoHandler()
            self.engine.info_handlers.append(self.infoHandler)

        self.api = Api(config['api']['url'], config['api']['token'])

        # Set up mongodb
        self.client = MongoClient(config['db']['host'])
        self.db = self.client.irwin
        if config['db']['authenticate']:
            self.db.authenticate(
                config['db']['authentication']['username'],
                config['db']['authentication']['password'], mechanism='MONGODB-CR')

        # Irwin
        self.irwinEnv = IrwinEnv(config, self.db)
        self.irwin = Irwin(self.irwinEnv, newmodel)

    def restartEngine(self):
        if self.engine:
            self.engine.kill()
            self.engine = uci.popen_engine(stockfish_command(self.config['stockfish']['update']))
            self.engine.setoption({'Threads': self.config['stockfish']['threads'], 'Hash': self.config['stockfish']['memory']})
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