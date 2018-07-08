"""Queue item for basic analysis by irwin"""
from default_imports import *

from modules.auth.Auth import AuthID
from modules.game.Game import PlayerID, GameID
from modules.queue.Origin import Origin, OriginReport, OriginModerator, OriginRandom

from datetime import datetime, timedelta

import pymongo
from pymongo.collection import Collection

import numpy as np
from math import ceil

EngineQueueID = NewType('EngineQueueID', str)
Precedence = NewType('Precedence', int)

class EngineQueue(NamedTuple('EngineQueue', [
        ('id', EngineQueueID),
        ('origin', Origin),
        ('gameIds', List[GameID])
        ('precedence', Precedence),
        ('complete', bool),
        ('owner', AuthID),
        ('date', datetime)
    ])):
    @staticmethod
    def new(playerId: PlayerID, origin: Origin, gamePredictions) -> EngineQueue:
        if len(gamePredictions) > 0:
            activations = sorted([(a[1]*a[1]) for a in gamePredictions], reverse=True)
            top30avg = ceil(np.average(activations[:ceil(0.3*len(activations))]))
        else:
            top30avg = 0
        precedence = top30avg
        if origin == OriginReport:
            precedence += 5000
        elif origin == OriginModerator:
            precedence = 100000
        return EngineQueue(
            id=playerId,
            origin=origin,
            precedence=precedence,
            owner=None,
            complete=False,
            date=datetime.now())

    def json(self) -> Dict:
        return {
            'id': self.id,
            'origin': self.origin,
            'precedence': self.precedence,
            'progress': self.progress,
            'complete': self.complete,
            'owner': self.owner,
            'date': "{:%d %b %Y at %H:%M}".format(self.date)
        }

    def complete(self) -> EngineQueue:
        return EngineQueue(
            id=self.id,
            origin=self.origin,
            precedence=self.precedence,
            complete=True,
            owner=self.owner,
            date=self.date)

class EngineQueueBSONHandler:
    @staticmethod
    def reads(bson: Dict) -> EngineQueue:
        return EngineQueue(
            id=bson['_id'],
            origin=bson['origin'],
            precedence=bson['precedence'],
            gameIds=bson.get('gameIds'),
            complete=bson.get('complete', False),
            owner=bson.get('owner'),
            date=bson.get('date'))

    @staticmethod
    @validate
    def writes(engineQueue: EngineQueue) -> Dict:
        return {
            '_id': engineQueue.id,
            'origin': engineQueue.origin,
            'precedence': engineQueue.precedence,
            'gameIds': engineQueue.gameIds,
            'complete': engineQueue.complete,
            'owner': engineQueue.owner,
            'date': datetime.now()
        }

class EngineQueueDB(NamedTuple('EngineQueueDB', [
        ('engineQueueColl', Collection)
    ])):
    def write(self, engineQueue: EngineQueue):
        self.engineQueueColl.update_one(
            {'_id': engineQueue.id},
            {'$set': EngineQueueBSONHandler.writes(engineQueue)}, upsert=True)

    def inProgress(self) -> List[EngineQueue]:
        return [EngineQueueBSONHandler.reads(bson) for bson in self.engineQueueColl.find({'owner': {'$ne': None}, 'complete': False})]

    def byId(self, _id: EngineQueueID) -> Opt[EngineQueue]:
        bson = self.engineQueueColl.find_one({'_id': _id})
        return None if bson is None else EngineQueueBSONHandler.reads(bson)

    def complete(self, engineQueue: EngineQueue):
        """remove a complete job from the queue"""
        self.write(engineQueue.complete())

    def updateComplete(self, _id: EngineQueueID, complete: bool):
        self.engineQueueColl.update_one(
            {'_id': _id},
            {'$set': {'complete': complete}})

    def removePlayerId(self, playerId: PlayerID):
        """remove all jobs related to playerId"""
        self.engineQueueColl.remove({'_id': playerId})

    def exists(self, playerId: PlayerID) -> bool:
        """playerId has a engineQueue object against their name"""
        return self.engineQueueColl.find_one({'_id': playerId}) is not None

    def owned(self, playerId: PlayerID) -> bool:
        """Does any deep player queue for playerId have an owner"""
        bson = self.engineQueueColl.find_one({'_id': playerId, 'owner': None})
        hasOwner = False
        if bson is not None:
            hasOwner = bson['owner'] is not None
        return hasOwner

    def oldest(self) -> Opt[EngineQueue]:
        bson = self.engineQueueColl.find_one(
            filter={'date': {'$lt': datetime.now() - timedelta(days=2)}},
            sort=[('date', pymongo.ASCENDING)])
        return None if bson is None else EngineQueueBSONHandler.reads(bson)

    def nextUnprocessed(self, name: AuthID) -> Opt[EngineQueue]:
        """find the next job to process against owner's name"""
        incompleteBSON = self.engineQueueColl.find_one({'owner': name, '$or': [{'complete': {'$exists': False}}, {'complete': False}]})
        if incompleteBSON is not None: # owner has unfinished business
            return EngineQueueBSONHandler.reads(incompleteBSON)

        engineQueueBSON = self.engineQueueColl.find_one_and_update(
            filter={'owner': None, 'complete': False},
            update={'$set': {'owner': name}},
            sort=[("precedence", pymongo.DESCENDING),
                ("date", pymongo.ASCENDING)])
        return None if engineQueueBSON is None else EngineQueueBSONHandler.reads(engineQueueBSON)

    def top(self, amount: int = 20) -> List[EngineQueue]:
        """Return the top `amount` of players, ranked by precedence"""
        bsons = self.engineQueueColl.find(
            filter={'complete': False},
            sort=[("precedence", pymongo.DESCENDING),
                ("date", pymongo.ASCENDING)]).limit(amount)
        return [EngineQueueBSONHandler.reads(b) for b in bsons]