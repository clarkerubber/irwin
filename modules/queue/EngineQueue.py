"""Queue item for basic analysis by irwin"""
from collections import namedtuple
from datetime import datetime, timedelta
from math import ceil
import pymongo
import numpy as np

class EngineQueue(namedtuple('EngineQueue', ['id', 'origin', 'precedence', 'progress', 'complete', 'owner', 'date'])):
    @staticmethod
    def new(userId, origin, gamePredictions):
        if len(gamePredictions) > 0:
            activations = sorted([(a[1]*a[1]) for a in gamePredictions], reverse=True)
            top30avg = ceil(np.average(activations[:ceil(0.3*len(activations))]))
        else:
            top30avg = 0
        precedence = top30avg
        if origin == 'report':
            precedence += 5000
        elif origin == 'moderator':
            precedence = 100000
        return EngineQueue(
            id=userId,
            origin=origin,
            precedence=precedence,
            owner=None,
            progress=0,
            complete=False,
            date=datetime.now())

    def json(self):
        return {
            'id': self.id,
            'origin': self.origin,
            'precedence': self.precedence,
            'progress': self.progress,
            'complete': self.complete,
            'owner': self.owner,
            'date': "{:%d %b %Y at %H:%M}".format(self.date)
        }

    def __complete__(self):
        return EngineQueue(
            id=self.id,
            origin=self.origin,
            precedence=self.precedence,
            progress=100,
            complete=True,
            owner=self.owner,
            date=self.date)

class EngineQueueBSONHandler:
    @staticmethod
    def reads(bson):
        return EngineQueue(
            id=bson['_id'],
            origin=bson['origin'],
            precedence=bson['precedence'],
            progress=bson.get('progress', 0),
            complete=bson.get('complete', False),
            owner=bson.get('owner'),
            date=bson.get('date'))

    @staticmethod
    def writes(engineQueue):
        return {
            '_id': engineQueue.id,
            'origin': engineQueue.origin,
            'precedence': engineQueue.precedence,
            'progress': engineQueue.progress,
            'complete': engineQueue.complete,
            'owner': engineQueue.owner,
            'date': datetime.now()
        }

class EngineQueueDB(namedtuple('EngineQueueDB', ['engineQueueColl'])):
    def write(self, engineQueue):
        self.engineQueueColl.update_one(
            {'_id': engineQueue.id},
            {'$set': EngineQueueBSONHandler.writes(engineQueue)}, upsert=True)

    def updateProgress(self, _id, progress):
        self.engineQueueColl.update_one(
            {'_id': _id},
            {'$set': {'progress': progress}})

    def inProgress(self):
        return [EngineQueueBSONHandler.reads(bson) for bson in self.engineQueueColl.find({'owner': {'$ne': None}, 'complete': False})]

    def byId(self, _id):
        bson = self.engineQueueColl.find_one({'_id': _id})
        return None if bson is None else EngineQueueBSONHandler.reads(bson)

    def complete(self, engineQueue):
        """remove a complete job from the queue"""
        self.write(engineQueue.__complete__())

    def updateComplete(self, _id, complete):
        self.engineQueueColl.update_one(
            {'_id': _id},
            {'$set': {'complete': complete}})

    def removeUserId(self, userId):
        """remove all jobs related to userId"""
        self.engineQueueColl.remove({'_id': userId})

    def exists(self, userId):
        """userId has a engineQueue object against their name"""
        return self.engineQueueColl.find_one({'_id': userId}) is not None

    def owned(self, userId):
        """Does any deep player queue for userId have an owner"""
        bson = self.engineQueueColl.find_one({'_id': userId, 'owner': None})
        hasOwner = False
        if bson is not None:
            hasOwner = bson['owner'] is not None
        return hasOwner

    def oldest(self):
        bson = self.engineQueueColl.find_one(
            filter={'date': {'$lt': datetime.now() - timedelta(days=2)}},
            sort=[('date', pymongo.ASCENDING)])
        return None if bson is None else EngineQueueBSONHandler.reads(bson)

    def nextUnprocessed(self, name):
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

    def top(self, amount=20):
        """Return the top `amount` of players, ranked by precedence"""
        bsons = self.engineQueueColl.find(
            filter={'complete': False},
            sort=[("precedence", pymongo.DESCENDING),
                ("date", pymongo.ASCENDING)]).limit(amount)
        return [EngineQueueBSONHandler.reads(b) for b in bsons]