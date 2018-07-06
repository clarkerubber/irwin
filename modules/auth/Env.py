from default_imports import *

from conf.ConfigWrapper import ConfigWrapper

from modules.auth.User import UserDB
from modules.auth.Token import TokenDB

from pymongo.database import Database

class Env:
    @validated
	def __init__(self, config: ConfigWrapper, db: Database):
		self.db = db
		self.userDB = UserDB(self.db[config.coll.user])
		self.tokenDB = TokenDB(self.db[config.coll.token])