from collections import namedtuple

class AnalysedGameActivation(namedtuple('AnalysedGameActivation', ['id', 'userId', 'engine', 'length', 'prediction'])):
    """
    id: String (gameId)
    userId: String (userId)
    engine: Bool (is the user and engine?)
    length: Int (length of the game in plys)
    prediction: Int (Irwin's last reported confidence that this user is a cheater)
    Used as a pivot coll for training.
    """
    @staticmethod
    def fromGamesAnalysisandPrediction(analysedGame, prediction, engine):
        return AnalysedGameActivation(
            id = analysedGame.id,
            userId = analysedGame.userId,
            engine = engine,
            length = len(analysedGame.analysedMoves),
            prediction = prediction)

class AnalysedGameActivationBSONHandler:
    @staticmethod
    def reads(bson):
        return AnalysedGameActivation(
            id = bson['_id'],
            userId = bson['userId'],
            engine = bson['engine'],
            length = bson['length'],
            prediction = bson['prediction'])

    @staticmethod
    def writes(cga):
        return {
            '_id': cga.id,
            'userId': cga.userId,
            'engine': cga.engine,
            'length': cga.length,
            'prediction': cga.prediction
        }

class AnalysedGameActivationDB(namedtuple('AnalysedGameActivationDB', ['confidentAnalysedGamePivotColl'])):
    def byUserId(self, userId):
        return [AnalysedGameActivationBSONHandler.reads(bson) for bson in self.confidentAnalysedGamePivotColl.find({'userId': userId})]

    def byEngineAndPrediction(self, engine, prediction):
        if engine:
            return [AnalysedGameActivationBSONHandler.reads(bson) for bson in self.confidentAnalysedGamePivotColl.find({'engine': engine, 'prediction': {'$gte': prediction}})]
        return [AnalysedGameActivationBSONHandler.reads(bson) for bson in self.confidentAnalysedGamePivotColl.find({'engine': engine, 'prediction': {'$lte': prediction}})]

    def write(self, cga): # Game
        self.confidentAnalysedGamePivotColl.update_one({'_id': cga.id}, {'$set': AnalysedGameActivationBSONHandler.writes(cga)}, upsert=True)

    def lazyWriteMany(self, cgas):
        [self.write(cga) for cga in cgas]