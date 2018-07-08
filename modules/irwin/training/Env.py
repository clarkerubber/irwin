from default_imports import *

from conf.ConfigWrapper import ConfigWrapper

from pymongo.database import Database

from modules.game.Player import PlayerDB
from modules.game.AnalysedGame import AnalysedGameDB

from modules.irwin.AnalysedGameActivation import AnalysedGameActivationDB

class Env:
    def __init__(self, config: ConfigWrapper, db: Database):
        self.config = config
        self.db = db

        self.playerDB = PlayerDB(db[self.config["game coll player"]])
        self.analysedGameDB = AnalysedGameDB(db[self.config["game coll analysed_game"]])
        self.analysedGameActivationDB = AnalysedGameActivationDB(db[self.config["irwin coll analysed_game_activation"]])