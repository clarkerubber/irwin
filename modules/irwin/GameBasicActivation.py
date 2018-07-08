"""Type used for pivot coll for basic game model training"""
from default_imports import *

from modules.game.Game import GameID, PlayerID

from pymongo.collection import Collection

GameBasicActivationID = NewType('GameBasicActivationID', str)
Prediction = NewType('Prediction', int)

class GameBasicActivation(NamedTuple('GameBasicActivation', [
        ('id', GameBasicActivationID),
        ('gameId', GameID),
        ('playerId', PlayerID),
        ('engine', bool),
        ('prediction', int)
    ])):
    @staticmethod
    def fromPrediction(gameId: GameID, playerId: PlayerID, prediction: Prediction, engine: bool) -> GameBasicActivation:
        return GameBasicActivation(
            id = gameId + '/' + playerId,
            gameId = gameId,
            playerId = playerId,
            engine = engine,
            prediction = prediction
            )

    @staticmethod
    def makeId(gameId: GameID, playerId: PlayerID) -> GameBasicActivationID:
        return gameId + '/' + playerId

class GameBasicActivationBSONHandler:
    @staticmethod
    def reads(bson: Dict) -> GameBasicActivation:
        return GameBasicActivation(
            id = bson['_id'],
            gameId = bson['gameId'],
            playerId = bson['playerId'],
            engine = bson['engine'],
            prediction = bson['prediction'])

    @staticmethod
    def writes(gba: GameBasicActivation) -> Dict:
        return {
            '_id': gba.id,
            'gameId': gba.gameId,
            'playerId': gba.playerId,
            'engine': gba.engine,
            'prediction': gba.prediction
        }

class GameBasicActivationDB(NamedTuple('GameBasicActivationDB', [
        ('gameBasicActivationColl', Collection)
    ])):
    def byPlayerId(self, playerId: PlayerID) -> List[GameBasicActivation]:
        return [GameBasicActivationBSONHandler.reads(bson) for bson in self.gameBasicActivationColl.find({'playerId': playerId})]

    def byEngineAndPrediction(self, engine: bool, prediction: Prediction) -> List[GameBasicActivation]:
        if engine:
            return [GameBasicActivationBSONHandler.reads(bson) for bson in self.gameBasicActivationColl.find({'engine': engine, 'prediction': {'$gte': prediction}})]
        return [GameBasicActivationBSONHandler.reads(bson) for bson in self.gameBasicActivationColl.find({'engine': engine, 'prediction': {'$lte': prediction}})]

    def write(self, gba: GameBasicActivation):
        self.gameBasicActivationColl.update_one({'_id': gba.id}, {'$set': GameBasicActivationBSONHandler.writes(gba)}, upsert=True)

    def lazyWriteMany(self, gbas: List[GameBasicActivation]):
        [self.write(gba) for gba in gbas]