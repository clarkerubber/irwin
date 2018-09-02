from default_imports import *

from modules.game.Player import PlayerID
from modules.game.AnalysedGame import AnalysedGame, AnalysedGameID

from modules.irwin.AnalysedGameModel import AnalysedGamePrediction

from pymongo.collection import Collection

Prediction = NewType('Prediction', int)

class AnalysedGameActivation(NamedTuple('AnalysedGameActivation', [
        ('id', AnalysedGameID),
        ('playerId', PlayerID),
        ('engine', bool),
        ('length', int),
        ('prediction', Prediction)]
    )):
    """
    Used as a pivot coll for training.
    """
    @staticmethod
    def fromAnalysedGameAndPrediction(analysedGame: AnalysedGame, prediction: AnalysedGamePrediction, engine: bool):
        return AnalysedGameActivation(
            id = analysedGame.id,
            playerId = analysedGame.playerId,
            engine = engine,
            length = len(analysedGame.analysedMoves),
            prediction = prediction.game)

class AnalysedGameActivationBSONHandler:
    @staticmethod
    def reads(bson: Dict) -> AnalysedGameActivation:
        return AnalysedGameActivation(
            id = bson['_id'],
            playerId = bson['playerId'],
            engine = bson['engine'],
            length = bson['length'],
            prediction = bson['prediction'])

    @staticmethod
    def writes(analysedGameActivation: AnalysedGameActivation) -> Dict:
        return {
            '_id': analysedGameActivation.id,
            'playerId': analysedGameActivation.playerId,
            'engine': analysedGameActivation.engine,
            'length': analysedGameActivation.length,
            'prediction': analysedGameActivation.prediction
        }

class AnalysedGameActivationDB(NamedTuple('AnalysedGameActivationDB', [
        ('confidentAnalysedGamePivotColl', Collection)
    ])):
    def byPlayerId(self, playerId: PlayerID) -> List[AnalysedGameActivation]:
        return [AnalysedGameActivationBSONHandler.reads(bson) for bson in self.confidentAnalysedGamePivotColl.find({'userId': playerId})]

    def byEngineAndPrediction(self, engine: bool, prediction: Prediction, limit = None) -> List[AnalysedGameActivation]:
        gtlt = '$gte' if engine else '$lte'
        pipeline = [{'$match': {'engine': engine, 'prediction': {gtlt: prediction}}}]

        if limit is not None:
            pipeline.append({'$sample': {'size': limit}})

        return [AnalysedGameActivationBSONHandler.reads(bson) for bson in self.confidentAnalysedGamePivotColl.aggregate(pipeline)]

    def write(self, analysedGameActivation: AnalysedGameActivation):
        self.confidentAnalysedGamePivotColl.update_one({'_id': analysedGameActivation.id}, {'$set': AnalysedGameActivationBSONHandler.writes(analysedGameActivation)}, upsert=True)

    def writeMany(self, analysedGameActivations: List[AnalysedGameActivation]):
        [self.write(analysedGameActivation) for analysedGameActivation in analysedGameActivations]