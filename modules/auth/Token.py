from default_imports import *

from modules.auth.Priv import Priv, PrivBSONHandler

from pymongo.collection import Collection

TokenID = NewType('TokenID', str)

class Token(NamedTuple('Token', [
        ('id', TokenID), 
        ('privs', List[Priv])
    ])):
    def hasPriv(self, priv: Priv) -> bool:
        return priv in self.privs

class TokenBSONHandler:
    @staticmethod
    def reads(bson: Dict) -> Token:
        return Token(
            id = bson['_id'],
            privs = [PrivBSONHandler.reads(p) for p in bson['privs']])

    @staticmethod
    def writes(token: Token) -> Dict:
        return {
            '_id': token.id,
            'privs': [PrivBSONHandler.writes(p) for p in token.privs]}

class TokenDB(NamedTuple('TokenDB', [
        ('coll', Collection)
    ])):
    def write(self, token: Token):
        self.coll.update_one({'_id': token.id}, {'$set': TokenBSONHandler.writes(token)}, upsert=True)

    def byId(self, _id: TokenID) -> Opt[Token]:
        doc = self.coll.find_one({'_id': _id})
        return None if doc is None else TokenBSONHandler.reads(doc)