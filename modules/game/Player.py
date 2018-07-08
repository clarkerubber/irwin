from default_imports import *

from datetime import datetime, timedelta
import pymongo
from pymongo.collection import Collection

from typing import NewType

PlayerID = NewType('PlayerID', str)

class Player(NamedTuple('Player', [
    ('id', 'PlayerID'),
    ('titled', bool),
    ('engine', bool),
    ('gamesPlayed', int),
    ('relatedCheaters', List['PlayerID'])])):
    @staticmethod
    def fromJson(data: Dict):
        user = data.get('user')
        assessment = data.get('assessment', {})
        try:
            return Player(
                id=user.get('id'),
                titled=user.get('title') is not None,
                engine=user.get('engine', False),
                gamesPlayed=assessment.get('user', {}).get('games', 0),
                relatedCheaters=assessment.get('relatedCheaters', []))
        except (RuntimeTypeError, AttributeError):
            return None
        return None

class PlayerBSONHandler:
    @staticmethod
    def reads(bson: Dict) -> Player:
        return Player(
                id = bson['_id'],
                titled = bson.get('titled', False),
                engine = bson['engine'],
                gamesPlayed = bson['gamesPlayed'],
                relatedCheaters = bson.get('relatedCheaters', [])
            )

    def writes(player: Player) -> Dict:
        return {
            '_id': player.id,
            'titled': player.titled,
            'engine': player.engine,
            'gamesPlayed': player.gamesPlayed,
            'relatedCheaters': player.relatedCheaters,
            'date': datetime.now()
        }

class PlayerDB(NamedTuple('PlayerDB', [
        ('playerColl', 'Collection')
    ])):
    def byId(self, playerId: PlayerID) -> Opt[Player]:
        playerBSON = self.playerColl.find_one({'_id': playerId})
        return None if playerBSON is None else PlayerBSONHandler.reads(playerBSON)

    def byPlayerId(self, playerId: PlayerID) -> Opt[Player]:
        return self.byId(playerId)

    def unmarkedByUserIds(self, playerIds: List[PlayerID]) -> List[Player]:
        return [(None if bson is None else PlayerBSONHandler.reads(bson))
            for bson in [self.playerColl.find_one({'_id': playerId, 'engine': False}) for playerId in playerIds]]

    def balancedSample(self, size: int) -> List[Player]:
        pipelines = [[
                {"$match": {"engine": True}},
                {"$sample": {"size": int(size/2)}}
            ],[
                {"$match": {"engine": False}},
                {"$sample": {"size": int(size/2)}}
            ]]
        engines = [PlayerBSONHandler.reads(p) for p in self.playerColl.aggregate(pipelines[0])]
        legits = [PlayerBSONHandler.reads(p) for p in self.playerColl.aggregate(pipelines[1])]
        return engines + legits

    def oldestNonEngine(self) -> Opt[Player]:
        playerBSON = self.playerColl.find_one_and_update(
            filter={'$or': [{'engine': False}, {'engine': None}], 'date': {'$lt': datetime.now() - timedelta(days=30)}},
            update={'$set': {'date': datetime.now()}},
            sort=[('date', pymongo.ASCENDING)])
        return None if playerBSON is None else PlayerBSONHandler.reads(playerBSON)

    def byEngine(self, engine: bool = True) -> List[Player]:
        return [PlayerBSONHandler.reads(p) for p in self.playerColl.find({'engine': engine})]

    def all(self) -> List[Player]:
        return [PlayerBSONHandler.reads(p) for p in self.playerColl.find({})]

    def write(self, player: Player):
        self.playerColl.update_one({'_id': player.id}, {'$set': PlayerBSONHandler.writes(player)}, upsert=True)