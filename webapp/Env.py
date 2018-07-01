import logging

from modules.auth.Auth import Auth
from modules.auth.Env import Env as AuthEnv

from modules.db.DBManager import DBManager

class Env:
    def __init__(self, settings):
        self.settings = settings
        ## Database
        self.dbManager = DBManager(settings)
        self.db = self.dbManager.db()
        
        ## Modules
        self.auth = Auth(AuthEnv(self.settings, self.db))