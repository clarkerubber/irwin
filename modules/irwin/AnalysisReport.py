from collections import namedtuple
from datetime import datetime
import random
import pymongo

class PlayerReport(namedtuple('PlayerReport', ['id', 'userId', 'owner', 'activation', 'date'])):
    @staticmethod
    def new(userId, owner, activation):
        reportId = str("%016x" % random.getrandbits(64))
        return PlayerReport(
            id=reportId,
            userId=userId,
            owner=owner,
            activation=activation,
            date=datetime.now())

    def reportDict(self, gameReports):
        return {
            'userId': self.userId,
            'owner': self.owner,
            'activation': int(self.activation),
            'games': [gameReport.reportDict() for gameReport in gameReports]
        }

class GameReport(namedtuple('GameReport', ['id', 'reportId', 'gameId', 'activation', 'moves'])):
    @staticmethod
    def new(gameAnalysis, gameActivation, gamePredictions, reportId, userId):
        gameId = gameAnalysis.gameId
        return GameReport(
            id=gameId + '/' + reportId,
            reportId=reportId,
            gameId=gameId,
            activation=gameActivation,
            moves=[MoveReport.new(am, p) for am, p in zip(gameAnalysis.moveAnalyses, movePredictions(gamePredictions[0]))])

    def reportDict(self):
        return {
            'gameId': self.gameId,
            'activation': self.activation,
            'moves': [move.reportDict() for move in self.moves]
        }

class MoveReport(namedtuple('MoveReport', ['activation', 'rank', 'ambiguity', 'advantage', 'loss'])):
    @staticmethod
    def new(analysedMove, movePrediction):
        return MoveReport(
            activation=moveActivation(movePrediction),
            rank=analysedMove.trueRank(),
            ambiguity=analysedMove.ambiguity(),
            advantage=int(100*analysedMove.advantage()),
            loss=int(100*analysedMove.winningChancesLoss()))

    def reportDict(self):
        return {
            'a': self.activation,
            'r': self.rank,
            'm': self.ambiguity,
            'o': self.advantage,
            'l': self.loss
        }

def movePredictions(gamePredictions):
    return list(zip(list(gamePredictions[1][0]), list(gamePredictions[2][0])))

def moveActivation(movePrediction):
    return int(50*(movePrediction[0][0]+movePrediction[1][0]))

class PlayerReportBSONHandler:
    @staticmethod
    def reads(bson):
        return PlayerReport(
            id=bson['_id'],
            userId=bson['userId'],
            owner=bson['owner'],
            activation=bson['activation'],
            date=bson['date']
            )

    @staticmethod
    def writes(playerReport):
        return {
            '_id': playerReport.id,
            'userId': playerReport.userId,
            'owner': playerReport.owner,
            'activation': playerReport.activation,
            'date': playerReport.date
        }

class GameReportBSONHandler:
    @staticmethod
    def reads(bson):
        return GameReport(
            id=bson['_id'],
            reportId=bson['reportId'],
            gameId=bson['gameId'],
            activation=bson['activation'],
            moves=[MoveReportBSONHandler.reads(mBson) for mBson in bson['moves']])

    @staticmethod
    def writes(gameReport):
        return {
            '_id': gameReport.id,
            'reportId': gameReport.reportId,
            'gameId': gameReport.gameId,
            'activation': gameReport.activation,
            'moves': [MoveReportBSONHandler.writes(move) for move in gameReport.moves]
        }

class MoveReportBSONHandler:
    @staticmethod
    def reads(bson):
        return MoveReport(
            activation=bson['a'],
            rank=bson['r'],
            ambiguity=bson['m'],
            advantage=bson['o'],
            loss=bson['l'])

    @staticmethod
    def writes(moveReport):
        return {
            'a': moveReport.activation,
            'r': moveReport.rank,
            'm': moveReport.ambiguity,
            'o': moveReport.advantage,
            'l': moveReport.loss
        }

class PlayerReportDB(namedtuple('PlayerReportDB', ['playerReportColl'])):
    def byUserId(self, userId):
        return [PlayerReportBSONHandler.reads(bson)
            for bson
            in self.playerReportColl.find(
                filter={'userId': userId},
                sort=[('date', pymongo.DESCENDING)])]

    def newestByUserId(self, userId):
        bson = self.playerReportColl.find_one(
            filter={'userId': userId},
            sort=[('date', pymongo.DESCENDING)])

    def byId(self, reportId):
        bson = self.playerReportColl.find_one({'_id': reportId})
        return None if bson is None else PlayerReportBSONHandler.reads(bson)

    def write(self, playerReport):
        self.playerReportColl.update_one(
            {'_id': playerReport.id},
            {'$set': PlayerReportBSONHandler.writes(playerReport)},
            upsert=True)

class GameReportDB(namedtuple('GameReportDB', ['gameReportColl'])):
    def byReportId(self, reportId):
        return [GameReportBSONHandler.reads(bson) for bson in self.gameReportColl.find({'reportId': reportId})]

    def byUserId(self, userId):
        return [GameReportBSONHandler.reads(bson) for bson in self.gameReportColl.find({'userId': userId})]

    def byGameId(self, gameId):
        return [GameReportBSONHandler.reads(bson) for bson in self.gameReportColl.find({'gameId': gameId})]

    def write(self, gameReport):
        self.gameReportColl.update_one(
            {'_id': gameReport.id},
            {'$set': GameReportBSONHandler.writes(gameReport)},
            upsert=True)

    def lazyWriteMany(self, gameReports):
        [self.write(gameReport) for gameReport in gameReports]