from default_imports import *

from conf.ConfigWrapper import ConfigWrapper

from pymongo import MongoClient
from pymongo.database import Database

class DBManager(NamedTuple('DBManager', [
        ('config', 'ConfigWrapper')
    ])):
    def client(self) -> MongoClient:
        return MongoClient(self.config.db.host)

    def db(self) -> Database:
        client = self.client()
        db = client[self.config['db database']]
        if self.config['db authenticate']:
            db.authenticate(
                self.config.authentication.username,
                self.config.authentication.password, mechanism='MONGODB-CR')
        return db