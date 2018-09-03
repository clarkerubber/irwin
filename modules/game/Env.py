from default_imports import *

from conf.ConfigWrapper import ConfigWrapper

from modules.game.Game import GameDB
from modules.game.AnalysedGame import AnalysedGameDB
from modules.game.Player import PlayerDB
from modules.game.AnalysedPosition import AnalysedPositionDB

from pymongo.database import Database

class Env:
    def __init__(self, config: ConfigWrapper, db: Database):
        self.config = config
        self.db = db

        self.gameDB = GameDB(self.db[self.config["game coll game"]])
        self.analysedGameDB = AnalysedGameDB(self.db[self.config["game coll analysed_game"]])
        self.playerDB = PlayerDB(self.db[self.config["game coll player"]])
        self.analysedPositionDB = AnalysedPositionDB(self.db[self.config["game coll analysed_position"]])