from modules.auth.User import UserDB
from modules.auth.Token import TokenDB
from collections import namedtuple
from pymongo import MongoClient

class Env:
	def __init__(self, config, db):
		self.db = db
		self.userDB = UserDB(self.db[config['auth']['coll']['user']])
		self.tokenDB = TokenDB(self.db[config['auth']['coll']['token']])