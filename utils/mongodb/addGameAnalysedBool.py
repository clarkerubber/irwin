from pymongo import MongoClient

client = MongoClient()
db = client.irwin
gameColl = db.game

for gBSON in gameColl.find({}):
    analysed = len(gBSON.get('analysis', [])) > 0
    gameColl.update_one({'_id': gBSON['_id']}, {'$set': {'analysed': analysed}})
