"""Queue item for deep analysis by irwin"""
from default_imports import *

from modules.queue.Origin import Origin
from modules.game.Game import PlayerID

from datetime import datetime
import pymongo
from pymongo.collection import Collection

IrwinQueue = NamedTuple('IrwinQueue', [
        ('id', PlayerID),
        ('origin', Origin)
    ])

class IrwinQueueBSONHandler:
    @staticmethod
    def reads(bson: Dict) -> IrwinQueue:
        return IrwinQueue(
            id=bson['_id'],
            origin=bson['origin'])

    @staticmethod
    def writes(irwinQueue: IrwinQueue) -> Dict:
        return {
            '_id': irwinQueue.id,
            'origin': irwinQueue.origin,
            'date': datetime.now()
        }

class IrwinQueueDB(NamedTuple('IrwinQueueDB', [
        ('irwinQueueColl', Collection)
    ])):
    def write(self, irwinQueue: IrwinQueue):
        self.irwinQueueColl.update_one(
            {'_id': irwinQueue.id}, 
            {'$set': IrwinQueueBSONHandler.writes(irwinQueue)},
            upsert=True)

    def removePlayerId(self, playerId: PlayerID):
        self.irwinQueueColl.remove({'_id': playerId})

    def nextUnprocessed(self) -> Opt[IrwinQueue]:
        irwinQueueBSON = self.irwinQueueColl.find_one_and_delete(
            filter={},
            sort=[("date", pymongo.ASCENDING)])
        return None if irwinQueueBSON is None else IrwinQueueBSONHandler.reads(irwinQueueBSON)