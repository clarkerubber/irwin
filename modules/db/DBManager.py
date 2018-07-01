from collections import namedtuple

from pymongo import MongoClient

class DBManager(namedtuple('DBManager', ['settings'])):
    def client(self):
        return MongoClient(self.settings['db']['host'])

    def db(self):
        client = self.client()
        db = client[self.settings['db']['database']]
        if self.settings['db']['authenticate']:
            db.authenticate(
                self.settings['db']['authentication']['username'],
                self.settings['db']['authentication']['password'], mechanism='MONGODB-CR')
        return db