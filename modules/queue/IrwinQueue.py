"""Queue item for deep analysis by irwin"""
from collections import namedtuple
from datetime import datetime
import pymongo

IrwinQueue = namedtuple('IrwinQueue', ['id', 'origin'])

class IrwinQueueBSONHandler:
    @staticmethod
    def reads(bson):
        return IrwinQueue(
            id=bson['_id'],
            origin=bson['origin'])

    @staticmethod
    def writes(irwinQueue):
        return {
            '_id': irwinQueue.id,
            'origin': irwinQueue.origin,
            'date': datetime.now()
        }

class IrwinQueueDB(namedtuple('IrwinQueueDB', ['irwinQueueColl'])):
    def write(self, irwinQueue):
        self.irwinQueueColl.update_one(
            {'_id': irwinQueue.id}, 
            {'$set': IrwinQueueBSONHandler.writes(irwinQueue)},
            upsert=True)

    def removeUserId(self, userId):
        self.irwinQueueColl.remove({'_id': userId})

    def nextUnprocessed(self):
        irwinQueueBSON = self.irwinQueueColl.find_one_and_delete(
            filter={},
            sort=[("date", pymongo.ASCENDING)])
        return None if irwinQueueBSON is None else IrwinQueueBSONHandler.reads(irwinQueueBSON)