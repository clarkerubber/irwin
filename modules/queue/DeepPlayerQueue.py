"""Queue item for basic analysis by irwin"""
from collections import namedtuple
from datetime import datetime
import pymongo

DeepPlayerQueue = namedtuple('DeepPlayerQueue', ['id', 'origin', 'precedence'])

class DeepPlayerQueueBSONHandler:
    @staticmethod
    def reads(bson):
        return DeepPlayerQueue(
            id=bson['_id'],
            origin=bson['origin'],
            precedence=bson['precedence'])

    @staticmethod
    def writes(deepPlayerQueue):
        return {
            '_id': deepPlayerQueue.id,
            'origin': deepPlayerQueue.origin,
            'precedence': deepPlayerQueue.precedence,
            'date': datetime.now()
        }

class DeepPlayerQueueDB(namedtuple('DeepPlayerQueueDB', ['deepPlayerQueueColl'])):
    def write(self, deepPlayerQueue):
        self.deepPlayerQueueColl.update_one(
            {'_id': deepPlayerQueue.id},
            {'$set': DeepPlayerQueueBSONHandler.writes(deepPlayerQueue)}, upsert=True)

    def nextUnprocessed(self):
        deepPlayerQueueBSON = self.deepPlayerQueueColl.find_one_and_delete(
            filter={},
            sort=[("precedence", pymongo.DESCENDING)])
        return None if deepPlayerQueueBSON is None else DeepPlayerQueueBSONHandler.reads(deepPlayerQueueBSON)