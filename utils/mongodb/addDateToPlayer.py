from pymongo import MongoClient
from datetime import datetime, timedelta

client = MongoClient()
db = client.irwin
playerColl = db.player

for pBSON in playerColl.find({}):
    if pBSON.get('date') is None:
        playerColl.update_one({'_id': pBSON['_id']}, {'$set': {'date': datetime.now() - timedelta(days=50)}})