from default_imports import *

from conf.ConfigWrapper import ConfigWrapper

from modules.auth.User import UserDB
from modules.auth.Token import TokenDB

from pymongo.database import Database

class Env:
    	def __init__(self, config: ConfigWrapper, db: Database):
		self.db = db
        self.config = config
		self.userDB = UserDB(self.db[self.config["auth coll user"]])
		self.tokenDB = TokenDB(self.db[self.config["auth coll token"]])