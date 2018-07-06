from enforce import runtime_validation
from typing import NamedTuple

from conf.ConfigWrapper import ConfigWrapper

from pymongo import MongoClient

@runtime_validation
class DBManager(NamedTuple('DBManager', [
    ('config', ConfigWrapper)])):
    @runtime_validation
    def client(self) -> MongoClient:
        return MongoClient(self.config['db']['host'])

    def db(self):
        client = self.client()
        db = client[self.config.database]
        if self.config.authenticate:
            db.authenticate(
                self.config.authentication.username,
                self.config.authentication.password, mechanism='MONGODB-CR')
        return db