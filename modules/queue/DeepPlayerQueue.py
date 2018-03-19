"""Queue item for basic analysis by irwin"""
from collections import namedtuple
from datetime import datetime, timedelta
from math import ceil
import pymongo
import numpy as np

class DeepPlayerQueue(namedtuple('DeepPlayerQueue', ['id', 'origin', 'precedence', 'progress', 'complete', 'owner', 'date'])):
    @staticmethod
    def new(userId, origin, gamePredictions):
        if len(gamePredictions) > 0:
            activations = sorted([(a[1]*a[1]) for a in gamePredictions], reverse=True)
            top30avg = ceil(np.average(activations[:ceil(0.3*len(activations))]))
        else:
            top30avg = 0
        originPrecedence = 0
        if origin == 'report':
            originPrecedence = 5000
        elif origin == 'moderator':
            originPrecedence = 100000
        return DeepPlayerQueue(
            id=userId,
            origin=origin,
            precedence=top30avg+originPrecedence,
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
        return DeepPlayerQueue(
            id=self.id,
            origin=self.origin,
            precedence=self.precedence,
            progress=100,
            complete=True,
            owner=self.owner,
            date=self.date)

class DeepPlayerQueueBSONHandler:
    @staticmethod
    def reads(bson):
        return DeepPlayerQueue(
            id=bson['_id'],
            origin=bson['origin'],
            precedence=bson['precedence'],
            progress=bson.get('progress', 0),
            complete=bson.get('complete', False),
            owner=bson.get('owner'),
            date=bson.get('date'))

    @staticmethod
    def writes(deepPlayerQueue):
        return {
            '_id': deepPlayerQueue.id,
            'origin': deepPlayerQueue.origin,
            'precedence': deepPlayerQueue.precedence,
            'progress': deepPlayerQueue.progress,
            'complete': deepPlayerQueue.complete,
            'owner': deepPlayerQueue.owner,
            'date': datetime.now()
        }

class DeepPlayerQueueDB(namedtuple('DeepPlayerQueueDB', ['deepPlayerQueueColl'])):
    def write(self, deepPlayerQueue):
        self.deepPlayerQueueColl.update_one(
            {'_id': deepPlayerQueue.id},
            {'$set': DeepPlayerQueueBSONHandler.writes(deepPlayerQueue)}, upsert=True)

    def updateProgress(self, _id, progress):
        self.deepPlayerQueueColl.update_one(
            {'_id': _id},
            {'$set': {'progress': progress}})

    def inProgress(self):
        return [DeepPlayerQueueBSONHandler.reads(bson) for bson in self.deepPlayerQueueColl.find({'owner': {'$ne': None}, 'complete': False})]

    def byId(self, _id):
        bson = self.deepPlayerQueueColl.find_one({'_id': _id})
        return None if bson is None else DeepPlayerQueueBSONHandler.reads(bson)

    def complete(self, deepPlayerQueue):
        """remove a complete job from the queue"""
        self.write(deepPlayerQueue.__complete__())

    def removeUserId(self, userId):
        """remove all jobs related to userId"""
        self.deepPlayerQueueColl.remove({'_id': userId})

    def exists(self, userId):
        """userId has a deepPlayerQueue object against their name"""
        return self.deepPlayerQueueColl.find_one({'_id': userId}) is not None

    def owned(self, userId):
        """Does any deep player queue for userId have an owner"""
        bson = self.deepPlayerQueueColl.find_one({'_id': userId, 'owner': None})
        hasOwner = False
        if bson is not None:
            hasOwner = bson['owner'] is not None
        return hasOwner

    def oldest(self):
        bson = self.deepPlayerQueueColl.find_one(
            filter={'date': {'$lt': datetime.now() - timedelta(days=2)}},
            sort=[('date', pymongo.ASCENDING)])
        return None if bson is None else DeepPlayerQueueBSONHandler.reads(bson)

    def nextUnprocessed(self, name):
        """find the next job to process"""
        incompleteBSON = self.deepPlayerQueueColl.find_one({'owner': name, '$or': [{'complete': {'$exists': False}}, {'complete': False}]})
        if incompleteBSON is not None: # owner has unfinished business
            return DeepPlayerQueueBSONHandler.reads(incompleteBSON)

        deepPlayerQueueBSON = self.deepPlayerQueueColl.find_one_and_update(
            filter={'owner': None, 'complete': False},
            update={'$set': {'owner': name}},
            sort=[("precedence", pymongo.DESCENDING),
                ("date", pymongo.ASCENDING)])
        return None if deepPlayerQueueBSON is None else DeepPlayerQueueBSONHandler.reads(deepPlayerQueueBSON)

    def top(self, amount=20):
        bsons = self.deepPlayerQueueColl.find(
            filter={'complete': False},
            sort=[("precedence", pymongo.DESCENDING),
                ("date", pymongo.ASCENDING)]).limit(amount)
        return [DeepPlayerQueueBSONHandler.reads(b) for b in bsons]