"""Queue item for basic analysis by irwin"""
from collections import namedtuple
from datetime import datetime, timedelta
import pymongo

class ModReport(namedtuple('ModReport', ['id', 'processed', 'created'])):
    @staticmethod
    def new(userId):
        return ModReport(
            id=userId,
            processed=False,
            created=datetime.now())

class ModReportBSONHandler:
    @staticmethod
    def reads(bson):
        return ModReport(
            id=bson['_id'],
            processed=bson['processed'],
            created=bson['created'])

    @staticmethod
    def writes(modReport):
        return {
            '_id': modReport.id,
            'processed': modReport.processed,
            'created': modReport.created,
            'updated': datetime.now()
        }

class ModReportDB(namedtuple('ModReportDB', ['modReportColl'])):
    @staticmethod
    def reader(bsons):
        return [ModReportBSONHandler.reads(b) for b in bsons]

    def write(self, modReport):
        self.modReportColl.update_one(
            {'_id': modReport.id}, 
            {'$set': ModReportBSONHandler.writes(modReport)},
            upsert=True)

    def close(self, userId):
        self.modReportColl.update_one(
            {'_id': userId},
            {'$set': {'processed': True, 'updated': datetime.now()}},
            upsert=False)

    def isOpen(self, userId):
        """ is there an open report against this player? """
        modReportBSON = self.modReportColl.find_one({'_id': userId})
        processed = True
        if modReportBSON is not None:
            processed = modReportBSON['processed']
        return not processed

    def allOpen(self, limit=None):
        """ all open, sorted by newest incase limit is set """
        return ModReportDB.reader(self.modReportColl.find(
                filter={'processed': False},
                sort=[('created', pymongo.DESCENDING)],
                batch_size=limit))

    def allNewest(self, limit=None):
        return self.allOpen(limit)

    def allOldest(self, limit=None):
        return ModReportDB.reader(self.modReportColl.find(
                filter={'processed': False},
                sort=[('created', pymongo.ASCENDING)],
                batch_size=limit))

    def oldestUnprocessed(self):
        modReportBSON = self.modReportColl.find_one_and_update(
            filter={'processed': False, 'updated': {'$lt': datetime.now() - timedelta(days=2)}},
            update={'$set': {'updated': datetime.now()}},
            sort=[('updated', pymongo.ASCENDING)])
        return None if modReportBSON is None else ModReportBSONHandler.reads(modReportBSON)