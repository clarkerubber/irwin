"""Type used for pivot coll for basic game model training"""
from collections import namedtuple

class GameBasicActivation(namedtuple('GameBasicActivation', ['id', 'gameId', 'userId', 'engine', 'prediction'])):
    @staticmethod
    def fromPrediction(gameId, userId, prediction, engine):
        return GameBasicActivation(
            id = gameId + '/' + userId,
            gameId = gameId,
            userId = userId,
            engine = engine,
            prediction = prediction
            )

    def color(self):
        darkColours = [
          'rgba(84, 231, 96, 0.8)',
          'rgba(109, 231, 84, 0.8)',
          'rgba(131, 231, 84, 0.8)',
          'rgba(163, 231, 84, 0.8)',
          'rgba(197, 231, 84, 0.8)',
          'rgba(231, 229, 84, 0.8)',
          'rgba(231, 194, 84, 0.8)',
          'rgba(231, 158, 84, 0.8)',
          'rgba(231, 118, 84, 0.8)',
          'rgba(231, 84, 84, 0.8)']

        return darkColours[int(self.prediction/10)]

class GameBasicActivationBSONHandler:
    @staticmethod
    def reads(bson):
        return GameBasicActivation(
            id = bson['_id'],
            gameId = bson['gameId'],
            userId = bson['userId'],
            engine = bson['engine'],
            prediction = bson['prediction'])

    @staticmethod
    def writes(gba):
        return {
            '_id': gba.id,
            'gameId': gba.gameId,
            'userId': gba.userId,
            'engine': gba.engine,
            'prediction': gba.prediction
        }

class GameBasicActivationDB(namedtuple('GameBasicActivationDB', ['gameBasicActivationColl'])):
    def byUserId(self, userId):
        return [GameBasicActivationBSONHandler.reads(bson) for bson in self.gameBasicActivationColl.find({'userId': userId})]

    def byEngineAndPrediction(self, engine, prediction):
        if engine:
            return [GameBasicActivationBSONHandler.reads(bson) for bson in self.gameBasicActivationColl.find({'engine': engine, 'prediction': {'$gte': prediction}})]
        return [GameBasicActivationBSONHandler.reads(bson) for bson in self.gameBasicActivationColl.find({'engine': engine, 'prediction': {'$lte': prediction}})]

    def write(self, gba): # Game
        self.gameBasicActivationColl.update_one({'_id': gba.id}, {'$set': GameBasicActivationBSONHandler.writes(gba)}, upsert=True)

    def lazyWriteMany(self, gbas):
        [self.write(gba) for gba in gbas]