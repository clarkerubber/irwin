from modules.auth.Priv import PrivBSONHandler
from collections import namedtuple

Token = namedtuple('Token', ['id', 'privs'])

class TokenBSONHandler:
	@staticmethod
	def reads(bson):
		return Token(
			id = bson['_id'],
			privs = [PrivBSONHandler.reads(p) for p in bson['privs']])

	@staticmethod
	def writes(token):
		return {
			'_id': token.id,
			'privs': [PrivBSONHandler.writes(p) for p in token.privs]}

class TokenDB(namedtuple('TokenDB', ['coll'])):
	def write(self, token):
		self.coll.update_one({'_id': token.id}, {'$set': TokenBSONHandler.writes(token)}, upsert=True)

	def byId(self, _id):
		doc = self.coll.find_one({'_id': _id})
		return None if doc is None else TokenBSONHandler.reads(doc)