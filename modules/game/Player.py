from collections import namedtuple
from datetime import datetime, timedelta
import pymongo

class Player(namedtuple('Player', ['id', 'titled', 'engine', 'gamesPlayed', 'relatedCheaters', 'reportScore', 'mustAnalyse'])):
    @staticmethod
    def fromPlayerData(data):
        user = data.get('user')
        assessment = data.get('assessment', {})
        if user is not None:
            return Player(
                id=user.get('id'),
                titled=user.get('title') is not None,
                engine=user.get('engine', False),
                gamesPlayed=assessment.get('user', {}).get('games', 0),
                relatedCheaters=assessment.get('relatedCheaters', []),
                reportScore=data.get('reportScore', None),
                mustAnalyse=[])
        return None

class PlayerBSONHandler:
    @staticmethod
    def reads(bson):
        return Player(
                id = bson['_id'],
                titled = bson.get('titled', False),
                engine = bson['engine'],
                gamesPlayed = bson['gamesPlayed'],
                relatedCheaters = bson.get('relatedCheaters', []),
                reportScore = bson.get('reportScore', None),
                mustAnalyse = bson.get('mustAnalyse', [])
            )

    def writes(player):
        return {
            '_id': player.id,
            'titled': player.titled,
            'engine': player.engine,
            'gamesPlayed': player.gamesPlayed,
            'relatedCheaters': player.relatedCheaters,
            'reportScore': player.reportScore,
            'mustAnalyse': player.mustAnalyse,
            'date': datetime.now()
        }

class PlayerDB(namedtuple('PlayerDB', ['playerColl'])):
    def byId(self, userId):
        playerBSON = self.playerColl.find_one({'_id': userId})
        return None if playerBSON is None else PlayerBSONHandler.reads(playerBSON)

    def byUserId(self, userId):
        return self.byId(userId)

    def unmarkedByUserIds(self, userIds):
        return [(None if bson is None else PlayerBSONHandler.reads(bson))
            for bson in [self.playerColl.find_one({'_id': userId, 'engine': False}) for userId in userIds]]

    def balancedSample(self, size):
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

    def oldestNonEngine(self):
        playerBSON = self.playerColl.find_one_and_update(
            filter={'$or': [{'engine': False}, {'engine': None}], 'date': {'$lt': datetime.now() - timedelta(months=1)}},
            update={'$set': {'date': datetime.now()}},
            sort=[('date', pymongo.ASCENDING)])
        return None if playerBSON is None else PlayerBSONHandler.reads(playerBSON)

    def byEngine(self, engine):
        return [PlayerBSONHandler.reads(p) for p in self.playerColl.find({'engine': engine})]

    def all(self):
        return [PlayerBSONHandler.reads(p) for p in self.playerColl.find({})]

    def write(self, player):
        self.playerColl.update_one({'_id': player.id}, {'$set': PlayerBSONHandler.writes(player)}, upsert=True)