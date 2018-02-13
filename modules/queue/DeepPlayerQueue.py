"""Queue item for basic analysis by irwin"""
from collections import namedtuple
from datetime import datetime
from math import ceil
import pymongo
import numpy as np

class DeepPlayerQueue(namedtuple('DeepPlayerQueue', ['id', 'origin', 'precedence', 'owner'])):
    @staticmethod
    def new(userId, origin, gamePredictions):
        activations = sorted([(a[1]*a[1]) for a in gamePredictions], reverse=True)
        top30avg = ceil(np.average(activations[:ceil(0.3*len(activations))]))
        originPrecedence = 0
        if origin == 'report':
            originPrecedence = 50
        elif origin == 'moderator':
            originPrecedence = 1000
        return DeepPlayerQueue(
            id = userId,
            origin = origin,
            precedence = top30avg+originPrecedence,
            owner = None)

class DeepPlayerQueueBSONHandler:
    @staticmethod
    def reads(bson):
        return DeepPlayerQueue(
            id=bson['_id'],
            origin=bson['origin'],
            precedence=bson['precedence'],
            owner=bson.get('owner'))

    @staticmethod
    def writes(deepPlayerQueue):
        return {
            '_id': deepPlayerQueue.id,
            'origin': deepPlayerQueue.origin,
            'precedence': deepPlayerQueue.precedence,
            'owner': deepPlayerQueue.owner,
            'date': datetime.now()
        }

class DeepPlayerQueueDB(namedtuple('DeepPlayerQueueDB', ['deepPlayerQueueColl'])):
    def write(self, deepPlayerQueue):
        self.deepPlayerQueueColl.update_one(
            {'_id': deepPlayerQueue.id},
            {'$set': DeepPlayerQueueBSONHandler.writes(deepPlayerQueue)}, upsert=True)

    def complete(self, deepPlayerQueue):
        # remove a complete job from the queue
        self.deepPlayerQueueColl.remove({'_id': deepPlayerQueue.id})

    def removeUserId(self, userId):
        self.deepPlayerQueueColl.remove({'_id': userId})

    def oldest(self):
        bson = self.deepPlayerQueueColl.find_one(
            filter={},
            sort=[('date', pymongo.ASCENDING)])
        return None if bson is None else DeepPlayerQueueBSONHandler.reads(bson)

    def nextUnprocessed(self, name):
        incompleteBSON = self.deepPlayerQueueColl.find_one({'owner': name})
        if incompleteBSON is not None: # owner has unfinished business
            return DeepPlayerQueueBSONHandler.reads(incompleteBSON)

        deepPlayerQueueBSON = self.deepPlayerQueueColl.find_one_and_update(
            filter={'owner': None},
            update={'$set': {'owner': name}},
            sort=[("precedence", pymongo.DESCENDING),
                ("date", pymongo.ASCENDING)])
        return None if deepPlayerQueueBSON is None else DeepPlayerQueueBSONHandler.reads(deepPlayerQueueBSON)