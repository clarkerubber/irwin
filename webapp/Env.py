from modules.db.DBManager import DBManager

from modules.auth.Auth import Auth
from modules.auth.Env import Env as AuthEnv

from modules.game.Env import Env as GameEnv
from modules.game.Api import Api as GameApi

import logging

class Env:
    def __init__(self, config):
        self.config = config
        
        ## Database
        self.dbManager = DBManager(config)
        self.db = self.dbManager.db()

        ## Envs
        self.authEnv = AuthEnv(self.config.auth, self.db)
        self.gameEnv = GameEnv(self.config.game, self.db)

        ## Modules
        self.auth = Auth(self.authEnv)
        self.gameApi = GameApi(self.gameEnv)