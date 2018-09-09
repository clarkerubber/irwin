"""Queue item for basic analysis by irwin"""
from default_imports import *

from modules.auth.Auth import AuthID
from modules.game.Game import Game, PlayerID, GameID
from modules.queue.Origin import Origin, OriginReport, OriginModerator, OriginRandom, maxOrigin

from datetime import datetime, timedelta

import pymongo
from pymongo.collection import Collection

import numpy as np
from math import ceil

EngineQueueID = NewType('EngineQueueID', str)
Precedence = NewType('Precedence', int)

class EngineQueue(NamedTuple('EngineQueue', [
        ('id', EngineQueueID), # same as player ID
        ('origin', Origin),
        ('requiredGameIds', List[GameID]), # games that must be analysed
        ('precedence', Precedence),
        ('completed', bool),
        ('owner', AuthID),
        ('date', datetime)
    ])):
    @staticmethod
    def new(playerId: PlayerID, origin: Origin, gamesAndPredictions: List[Tuple[Game, int]]):
        if len(gamesAndPredictions) > 0:
            gamesAndPredictions = sorted(gamesAndPredictions, key=lambda gap: gap[1], reverse=True)
            required = [gap[0].id for gap in gamesAndPredictions][:10]
            activations = [gap[1]**2 for gap in gamesAndPredictions]
            top30avg = ceil(np.average(activations[:ceil(0.3*len(activations))]))
        else:
            required = []
            top30avg = 0
        
        # set the precedence to the top30avg
        precedence = top30avg

        # then modify it depending on where it came from
        if origin == OriginReport:
            precedence += 5000
        elif origin == OriginModerator:
            precedence = 100000

        return EngineQueue(
            id=playerId,
            origin=origin,
            requiredGameIds=required,
            precedence=precedence,
            owner=None,
            completed=False,
            date=datetime.now())

    def complete(self):
        return EngineQueue(
            id=self.id,
            origin=self.origin,
            requiredGameIds=self.requiredGameIds,
            precedence=self.precedence,
            completed=True,
            owner=self.owner,
            date=self.date)

    @staticmethod
    def merge(engineQueueA, engineQueueB):
        return EngineQueue(
            id=engineQueueA.id,
            origin=maxOrigin(engineQueueA.origin, engineQueueB.origin),
            requiredGameIds=engineQueueA.requiredGameIds + engineQueueB.requiredGameIds,
            precedence=max(engineQueueA.precedence, engineQueueB.precedence),
            completed=min(engineQueueA.completed, engineQueueB.completed),
            owner=engineQueueA.owner if engineQueueA.owner is not None else (engineQueueB.owner if engineQueueB.owner is not None else None),
            date=min(engineQueueA.date, engineQueueB.date)) # retain the oldest datetime so the sorting doesn't mess up

class EngineQueueBSONHandler:
    @staticmethod
    def reads(bson: Dict) -> EngineQueue:
        return EngineQueue(
            id=bson['_id'],
            origin=bson['origin'],
            precedence=bson['precedence'],
            requiredGameIds=bson.get('requiredGameIds', []),
            completed=bson.get('complete', False),
            owner=bson.get('owner'),
            date=bson.get('date'))

    @staticmethod
    def writes(engineQueue: EngineQueue) -> Dict:
        return {
            '_id': engineQueue.id,
            'origin': engineQueue.origin,
            'precedence': engineQueue.precedence,
            'requiredGameIds': engineQueue.requiredGameIds,
            'completed': engineQueue.completed,
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
        return [EngineQueueBSONHandler.reads(bson) for bson in self.engineQueueColl.find({'owner': {'$ne': None}, 'completed': False})]

    def byId(self, _id: EngineQueueID) -> Opt[EngineQueue]:
        bson = self.engineQueueColl.find_one({'_id': _id})
        return None if bson is None else EngineQueueBSONHandler.reads(bson)

    def byPlayerId(self, playerId: str) -> Opt[EngineQueue]:
        return self.byId(playerId)

    def complete(self, engineQueue: EngineQueue):
        """remove a complete job from the queue"""
        self.write(engineQueue.complete())

    def updateComplete(self, _id: EngineQueueID, complete: bool):
        self.engineQueueColl.update_one(
            {'_id': _id},
            {'$set': {'completed': complete}})

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
        incompleteBSON = self.engineQueueColl.find_one({'owner': name, '$or': [{'completed': {'$exists': False}}, {'completed': False}]})
        if incompleteBSON is not None: # owner has unfinished business
            logging.debug(f'{name} is returning to complete {incompleteBSON}')
            return EngineQueueBSONHandler.reads(incompleteBSON)

        engineQueueBSON = self.engineQueueColl.find_one_and_update(
            filter={'owner': None, 'completed': False},
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