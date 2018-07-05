from modules.db.DBManager import DBManager

from modules.auth.Auth import Auth
from modules.auth.Env import Env as AuthEnv

from modules.game.Env import Env as GameEnv
from modules.game.Api import Api as GameApi

import logging

class Env:
    def __init__(self, settings):
        self.settings = settings
        
        ## Database
        self.dbManager = DBManager(settings)
        self.db = self.dbManager.db()

        ## Envs
        self.authEnv = AuthEnv(self.settings, self.db)
        self.gameEnv = GameEnv(self.settings, self.db)

        ## Modules
        self.auth = Auth(self.authEnv)
        self.gameApi = GameApi(self.gameEnv)