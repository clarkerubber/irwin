"""Type used for pivot coll for basic game model training"""
from default_imports import *

from modules.game.Game import GameID, PlayerID

from pymongo.collection import Collection

BasicGameActivationID = NewType('BasicGameActivationID', str)
Prediction = NewType('Prediction', int)

class BasicGameActivation(NamedTuple('BasicGameActivation', [
        ('id', BasicGameActivationID),
        ('gameId', GameID),
        ('playerId', PlayerID),
        ('engine', bool),
        ('prediction', int)
    ])):
    @staticmethod
    def fromPrediction(gameId: GameID, playerId: PlayerID, prediction: Prediction, engine: bool):
        return BasicGameActivation(
            id = gameId + '/' + playerId,
            gameId = gameId,
            playerId = playerId,
            engine = engine,
            prediction = prediction
            )

    @staticmethod
    def makeId(gameId: GameID, playerId: PlayerID) -> BasicGameActivationID:
        return gameId + '/' + playerId

class BasicGameActivationBSONHandler:
    @staticmethod
    def reads(bson: Dict) -> BasicGameActivation:
        return BasicGameActivation(
            id = bson['_id'],
            gameId = bson['gameId'],
            playerId = bson['playerId'],
            engine = bson['engine'],
            prediction = bson['prediction'])

    @staticmethod
    def writes(gba: BasicGameActivation) -> Dict:
        return {
            '_id': gba.id,
            'gameId': gba.gameId,
            'playerId': gba.playerId,
            'engine': gba.engine,
            'prediction': gba.prediction
        }

class BasicGameActivationDB(NamedTuple('BasicGameActivationDB', [
        ('basicGameActivationColl', Collection)
    ])):
    def byPlayerId(self, playerId: PlayerID) -> List[BasicGameActivation]:
        return [BasicGameActivationBSONHandler.reads(bson) for bson in self.basicGameActivationColl.find({'playerId': playerId})]

    def byEngineAndPrediction(self, engine: bool, prediction: Prediction) -> List[BasicGameActivation]:
        if engine:
            return [BasicGameActivationBSONHandler.reads(bson) for bson in self.basicGameActivationColl.find({'engine': engine, 'prediction': {'$gte': prediction}})]
        return [BasicGameActivationBSONHandler.reads(bson) for bson in self.basicGameActivationColl.find({'engine': engine, 'prediction': {'$lte': prediction}})]

    def write(self, gba: BasicGameActivation):
        self.basicGameActivationColl.update_one({'_id': gba.id}, {'$set': BasicGameActivationBSONHandler.writes(gba)}, upsert=True)

    def writeMany(self, gbas: List[BasicGameActivation]):
        [self.write(gba) for gba in gbas]