"""Queue item for basic analysis by irwin"""
from collections import namedtuple
from datetime import datetime
import pymongo

BasicPlayerQueue = namedtuple('BasicPlayerQueue', ['id', 'origin'])

class BasicPlayerQueueBSONHandler:
    @staticmethod
    def reads(bson):
        return BasicPlayerQueue(
            id=bson['_id'],
            origin=bson['origin'])

    @staticmethod
    def writes(basicPlayerQueue):
        return {
            '_id': basicPlayerQueue.id,
            'origin': basicPlayerQueue.origin,
            'date': datetime.now()
        }

class BasicPlayerQueueDB(namedtuple('BasicPlayerQueueDB', ['basicPlayerQueueColl'])):
    def write(self, basicPlayerQueue):
        self.basicPlayerQueueColl.update_one({'_id': basicPlayerQueue.id}, {'$set': BasicPlayerQueueBSONHandler.writes(basicPlayerQueue)}, upsert=True)

    def nextUnprocessed(self):
        basicPlayerQueueBSON = self.basicPlayerQueueColl.find_one_and_delete(
            filter={},
            sort=[("date", pymongo.DESCENDING)])
        return None if basicPlayerQueueBSON is None else BasicPlayerQueueBSONHandler.reads(basicPlayerQueueBSON)