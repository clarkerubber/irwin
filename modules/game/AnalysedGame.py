from math import log10, floor
import logging
import numpy as np
import json

from modules.game.AnalysedMove import AnalysedMove, AnalysedMoveBSONHandler, EngineEval, Analysis
from modules.game.AnalysedPosition import AnalysedPosition

from collections import namedtuple

def round_sig(x, sig=2):
    if x == 0:
        return 0
    return round(x, sig-int(floor(log10(abs(x))))-1)

class AnalysedGame(namedtuple('AnalysedGame', ['id', 'userId', 'gameId', 'analysedMoves'])):
    @staticmethod
    def new(gameId, white, userId, analysedMoves):
        return AnalysedGame(
            id=AnalysedGame.makeId(gameId, white),
            userId=userId,
            gameId=gameId,
            analysedMoves=analysedMoves)

    @staticmethod
    def makeId(gameId, white):
        return gameId + '/' + ('white' if white else 'black')

    def tensor(self, length=60):
        emtAvg = self.emtAverage()
        wclAvg = self.wclAverage()
        ts = [ma.tensor(emtAvg, wclAvg) for ma in self.analysedMoves]
        ts = ts[:length]
        ts = ts + (length-len(ts))*[AnalysedMove.nullTensor()]
        return np.array(ts)

    def emtAverage(self):
        return np.average([m.emt for m in self.analysedMoves])

    def wclAverage(self):
        return np.average([m.winningChancesLoss() for m in self.analysedMoves])

    def gameLength(self):
        return len(self.analysedMoves)

    def blurs(self):
        return [move.blur for move in self.analysedMoves]

    def emts(self):
        return [m.emt for m in self.analysedMoves]

    def emtSeconds(self):
        return [emt/100 for emt in self.emts()]

    def winningChances(self):
        return [m.advantage() for m in self.analysedMoves]

    def winningChancesPercent(self):
        return [100*m.advantage() for m in self.analysedMoves]

    def winningChancesLossPercent(self, usePV=True):
        return [100*m.winningChancesLoss(usePV=usePV) for m in self.analysedMoves]

    def winningChancesLossByPV(self):
        """ for generating graphs """
        pvs = [(
            'PV'+str(i+1),
            'rgba(20, 20, 20, ' + str(0.6 - i*0.1) + ')',
            []) for i in range(5)] # one entry per PV
        for analysedMove in self.analysedMoves:
            losses = analysedMove.PVsWinningChancesLoss()
            for i in range(5):
                try:
                    pvs[i][2].append(max(0, 100*losses[i]))
                except IndexError:
                    pvs[i][2].append('null')
        return pvs

    def ranks(self):
        """ for generating graphs """
        return [move.trueRank() for move in self.analysedMoves]

    def ambiguities(self):
        """ for generating graphs """
        return [move.ambiguity() for move in self.analysedMoves]

    def length(self):
        return len(self.analysedMoves)

    def ranksJSON(self):
        return json.dumps(self.ranks())

    def binnedSeconds(self, bins=10):
        # JSON format for graphing
        emts = self.emts()
        minSec = min(emts)
        maxSec = max(emts)
        step = int((maxSec-minSec)/bins)
        data = [[] for i in range(bins)]
        labels = [[] for i in range(bins)]
        for i, stepStart in enumerate(range(minSec, maxSec, step)):
            data[min(bins-1, i)] = len([a for a in emts if a >= stepStart and a <= stepStart+step])
            labels[min(bins-1, i)] = str(round_sig(stepStart/100)) + '-' + str(round_sig((stepStart+step)/100)) + 's'
        return {'data': json.dumps(data), 'labels': json.dumps(labels)}

    def binnedLosses(self, bins=10):
        # JSON format for graphing
        losses = self.winningChancesLossPercent()
        data = [[] for i in range(bins+1)]
        for i in range(0, bins, 1):
            data[min(bins-1,i)] = len([a for a in losses if i == int(a)])
        data[bins] = sum([int(a >= 10) for a in losses])
        labels = [('-' + str(a) + '%') for a in range(bins)]
        labels.append('Other')
        return {'data': json.dumps(data), 'labels': json.dumps(labels)}

    def binnedPVs(self, bins=6):
        # JSON format for graphing
        pvs = self.ranks()
        data = [[] for i in range(bins)]
        for i, p in enumerate([1, 2, 3, 4, 5, None]):
            data[i] = len([1 for pv in pvs if pv == p])
        labels = ['PV 1', 'PV 2', 'PV 3', 'PV 4', 'PV 5', 'Other']
        return {'data': json.dumps(data), 'labels': json.dumps(labels)}

    def moveRankByTime(self):
        return [{'x': time, 'y': rank} for rank, time in zip(self.ranks(), self.emtSeconds())]

    def moveRankByTimeJSON(self):
        # json format for graphing
        return json.dumps(self.moveRankByTime())

    def lossByTime(self):
        return [{'x': time, 'y': loss} for loss, time in zip(self.winningChancesLossPercent(), self.emtSeconds())]

    def lossByTimeJSON(self):
        # json format for graphing
        return json.dumps(self.lossByTime())

    def lossByRank(self):
        return [{'x': rank, 'y': loss} for loss, rank in zip(self.winningChancesLossPercent(), self.ranks())]

    def lossByRankJSON(self):
        # json format for graphing
        return json.dumps(self.lossByRank())

class AnalysedGameBSONHandler:
    @staticmethod
    def reads(bson):
        return AnalysedGame(
            id = bson['_id'],
            userId = bson['userId'],
            gameId = bson['gameId'],
            analysedMoves = [AnalysedMoveBSONHandler.reads(am) for am in bson['analysis']])

    @staticmethod
    def writes(analysedGame):
        return {
            '_id': analysedGame.id,
            'userId': analysedGame.userId,
            'gameId': analysedGame.gameId,
            'analysis': [AnalysedMoveBSONHandler.writes(am) for am in analysedGame.analysedMoves]
        }

class AnalysedGameDB(namedtuple('AnalysedGameDB', ['analysedGameColl'])):
    def write(self, analysedGame):
        self.analysedGameColl.update_one(
            {'_id': analysedGame.id},
            {'$set': AnalysedGameBSONHandler.writes(analysedGame)},
            upsert=True)

    def lazyWriteAnalysedGames(self, analysedGames):
        [self.write(ga) for ga in analysedGames]

    def byUserId(self, userId):
        return [AnalysedGameBSONHandler.reads(ga) for ga in self.analysedGameColl.find({'userId': userId})]

    def byUserIds(self, userIds):
        return [self.byUserId(userId) for userId in userIds]

    def byIds(self, ids):
        return [AnalysedGameBSONHandler.reads(ga) for ga in self.analysedGameColl.find({"_id": {"$in": ids}})]

    def allBatch(self, batch, batchSize=500):
        return [AnalysedGameBSONHandler.reads(ga) for ga in self.analysedGameColl.find(skip=batch*batchSize, limit=batchSize)]

    def byGameIdAndUserId(self, gameId, userId):
        bson = self.analysedGameColl.find_one({'gameId': gameId, 'userId': userId})
        return None if bson is None else AnalysedGameBSONHandler.reads(bson)