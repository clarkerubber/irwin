from default_imports import *

from modules.auth.Priv import Priv, PrivBSONHandler

from pymongo.collection import Collection

TokenID = TypeVar('TokenID', str)

@validated
class Token(NamedTuple('Token', [
        ('id', TokenID), 
        ('privs', List[Priv])
    ])):
    @validated
	def hasPriv(self, priv: Priv) -> bool:
		return priv in self.privs

class TokenBSONHandler:
	@staticmethod
    @validated
	def reads(bson: Dict) -> Token:
		return Token(
			id = bson['_id'],
			privs = [PrivBSONHandler.reads(p) for p in bson['privs']])

	@staticmethod
    @validated
	def writes(token: Token) -> Dict:
		return {
			'_id': token.id,
			'privs': [PrivBSONHandler.writes(p) for p in token.privs]}

@validated
class TokenDB(NamedTuple('TokenDB', [
        ('coll', Collection)
    ])):
    @validated
	def write(self, token: Token):
		self.coll.update_one({'_id': token.id}, {'$set': TokenBSONHandler.writes(token)}, upsert=True)

    @validated
	def byId(self, _id: TokenId) -> Opt[Token]:
		doc = self.coll.find_one({'_id': _id})
		return None if doc is None else TokenBSONHandler.reads(doc)