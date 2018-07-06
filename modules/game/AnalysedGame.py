from default_imports import *

from math import log10, floor
import logging
import numpy as np
import json

from modules.game.Game import GameID, Blur, Emt
from modules.game.Colour import Colour
from modules.game.Player import PlayerID
from modules.game.AnalysedMove import AnalysedMove, AnalysedMoveBSONHandler, EngineEval, Analysis
from modules.game.AnalysedPosition import AnalysedPosition

from pymongo.collection import Collection

AnalysedGameID = NewType('AnalysedGameID', str)

AnalysedGameTensor = NewType('AnalysedGameTensor', np.ndarray)

@validated
class AnalysedGame(NamedTuple('AnalysedGame', [
        ('id', AnalysedGameID),
        ('playerId', PlayerID),
        ('gameId', GameID),
        ('analysedMoves', List[AnalysedMove])
    ])):
    """
    An analysed game is a game that has been deeply analysed from a single
    player's perspective.
    """
    @staticmethod
    @validated
    def new(gameId: GameID, colour: Colour, playerId: PlayerID, analysedMoves: List[AnalysedMove]) -> AnalysedGame:
        return AnalysedGame(
            id=AnalysedGame.makeId(gameId, colour),
            playerId=playerId,
            gameId=gameId,
            analysedMoves=analysedMoves)

    @staticmethod
    @validated
    def makeId(gameId: GameID, colour: Colour) -> AnalysedGameID:
        return gameId + '/' + ('white' if colour else 'black')

    @validated
    def tensor(self, length: int = 60) -> AnalysedGameTensor:
        emtAvg = self.emtAverage()
        wclAvg = self.wclAverage()
        ts = [ma.tensor(emtAvg, wclAvg) for ma in self.analysedMoves]
        ts = ts[:length]
        ts = ts + (length-len(ts))*[AnalysedMove.nullTensor()]
        return np.array(ts)

    @validated
    def emtAverage(self) -> Number:
        return np.average([m.emt for m in self.analysedMoves])

    @validated
    def wclAverage(self) -> Number:
        return np.average([m.winningChancesLoss() for m in self.analysedMoves])

    @validated
    def gameLength(self) -> int:
        return len(self.analysedMoves)

    @validated
    def blurs(self) -> List[Blur]:
        return [move.blur for move in self.analysedMoves]

    @validated
    def emts(self) -> List[Emt]:
        return [m.emt for m in self.analysedMoves]

    @validated
    def emtSeconds(self) -> List[Number]:
        return [emt/100 for emt in self.emts()]

    @validated
    def winningChances(self) -> List[Number]:
        return [m.advantage() for m in self.analysedMoves]

    @validated
    def winningChancesPercent(self) -> List[Number]:
        return [100*m.advantage() for m in self.analysedMoves]

    @validated
    def winningChancesLossPercent(self, usePV: bool = True) -> List[Number]:
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

    @validated
    def ranks(self) -> List[Rank]:
        """ for generating graphs """
        return [move.trueRank() for move in self.analysedMoves]

    @validated
    def ambiguities(self) -> List[int]:
        """ for generating graphs """
        return [move.ambiguity() for move in self.analysedMoves]

    @validated
    def length(self) -> int:
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

def round_sig(x, sig=2):
    if x == 0:
        return 0
    return round(x, sig-int(floor(log10(abs(x))))-1)

class AnalysedGameBSONHandler:
    @staticmethod
    @validated
    def reads(bson: Dict) -> AnalysedGame:
        return AnalysedGame(
            id = bson['_id'],
            playerId = bson['playerId'],
            gameId = bson['gameId'],
            analysedMoves = [AnalysedMoveBSONHandler.reads(am) for am in bson['analysis']])

    @staticmethod
    @validated
    def writes(analysedGame: AnalysedGame) -> Dict:
        return {
            '_id': analysedGame.id,
            'playerId': analysedGame.playerId,
            'gameId': analysedGame.gameId,
            'analysis': [AnalysedMoveBSONHandler.writes(am) for am in analysedGame.analysedMoves]
        }

@validated
class AnalysedGameDB(NamedTuple('AnalysedGameDB', [
        ('analysedGameColl', Collection)
    ])):
    @validated
    def write(self, analysedGame: AnalysedGame):
        self.analysedGameColl.update_one(
            {'_id': analysedGame.id},
            {'$set': AnalysedGameBSONHandler.writes(analysedGame)},
            upsert=True)

    @validated
    def lazyWriteAnalysedGames(self, analysedGames: List[AnalysedGame]):
        [self.write(ga) for ga in analysedGames]

    @validated
    def byUserId(self, playerId: PlayerID) -> List[AnalysedGame]:
        return [AnalysedGameBSONHandler.reads(ga) for ga in self.analysedGameColl.find({'playerId': playerId})]

    @validated
    def byUserIds(self, playerIds: List[PlayerID]) -> List[AnalysedGame]:
        return [self.byUserId(playerId) for playerId in playerIds]

    @validated
    def byIds(self, ids: List[AnalysedGameID]) -> List[AnalysedGame]:
        return [AnalysedGameBSONHandler.reads(ga) for ga in self.analysedGameColl.find({"_id": {"$in": ids}})]

    @validated
    def allBatch(self, batch: int, batchSize: int = 500):
        """
        Gets all analysed games in a paged format
        batch = page number
        batchSize = size of page
        """
        return [AnalysedGameBSONHandler.reads(ga) for ga in self.analysedGameColl.find(skip=batch*batchSize, limit=batchSize)]

    @validated
    def byGameIdAndUserId(self, gameId: GameID, playerId: PlayerID) -> Opt[AnalysedGame]:
        bson = self.analysedGameColl.find_one({'gameId': gameId, 'playerId': playerId})
        return None if bson is None else AnalysedGameBSONHandler.reads(bson)