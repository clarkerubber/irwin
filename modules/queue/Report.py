"""Queue item for basic analysis by irwin"""
from collections import namedtuple
from datetime import datetime, timedelta
import pymongo

class Report(namedtuple('Report', ['id', 'processed', 'created'])):
    @staticmethod
    def new(userId):
        return Report(
            id=userId,
            processed=False,
            created=datetime.now())

class ReportBSONHandler:
    @staticmethod
    def reads(bson):
        return Report(
            id=bson['_id'],
            processed=bson['processed'],
            created=bson['created'])

    @staticmethod
    def writes(report):
        return {
            '_id': report.id,
            'processed': report.processed,
            'created': report.created,
            'updated': datetime.now()
        }

class ReportDB(namedtuple('ReportDB', ['reportColl'])):
    def write(self, report):
        self.reportColl.update_one(
            {'_id': report.id}, 
            {'$set': ReportBSONHandler.writes(report)},
            upsert=True)

    def close(self, userId):
        self.reportColl.update_one(
            {'_id': userId},
            {'$set': {'processed': True, 'updated': datetime.now()}},
            upsert=False)

    def isOpen(self, userId):
        reportBSON = self.reportColl.find_one({'_id': userId})
        processed = False
        if reportBSON is not None:
            processed = reportBSON['processed']
        return processed

    def oldestUnprocessed(self):
        reportBSON = self.reportColl.find_one_and_update(
            filter={'processed': False, 'updated': {'$lt': datetime.now() - timedelta(days=2)}},
            update={'$set': {'updated': datetime.now()}},
            sort=[('updated', pymongo.ASCENDING)])
        return None if reportBSON is None else ReportBSONHandler.reads(reportBSON)