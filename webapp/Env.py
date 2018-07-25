from modules.db.DBManager import DBManager

from modules.auth.Auth import Auth
from modules.auth.Env import Env as AuthEnv

from modules.game.Env import Env as GameEnv
from modules.game.Api import Api as GameApi

from modules.queue.Env import Env as QueueEnv
from modules.queue.Queue import Queue

import logging

class Env:
    def __init__(self, config):
        self.config = config
        
        ## Database
        self.dbManager = DBManager(self.config)
        self.db = self.dbManager.db()

        ## Envs
        self.authEnv = AuthEnv(self.config, self.db)
        self.gameEnv = GameEnv(self.config, self.db)
        self.queueEnv = QueueEnv(self.config, self.db)

        ## Modules
        self.auth = Auth(self.authEnv)
        self.gameApi = GameApi(self.gameEnv)
        self.queue = Queue(self.queueEnv)