from default_imports import *

from math import log10, floor
import numpy as np
import json

from modules.game.Game import Game, GameID, Emt
from modules.game.Colour import Colour
from modules.game.Player import PlayerID
from modules.game.AnalysedMove import AnalysedMove, AnalysedMoveBSONHandler, EngineEval, Analysis, Rank, TrueRank
from modules.game.AnalysedPosition import AnalysedPosition

from pymongo.collection import Collection

AnalysedGameID = NewType('AnalysedGameID', str) # <GameID>/<white|black>

AnalysedGameTensor = NewType('AnalysedGameTensor', np.ndarray)

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
    def new(gameId: GameID, colour: Colour, playerId: PlayerID, analysedMoves: List[AnalysedMove]):
        return AnalysedGame(
            id=AnalysedGame.makeId(gameId, colour),
            playerId=playerId,
            gameId=gameId,
            analysedMoves=analysedMoves)

    @staticmethod
    def makeId(gameId: GameID, colour: Colour) -> AnalysedGameID:
        return gameId + '/' + ('white' if colour else 'black')

    def tensor(self, length: int = 60) -> AnalysedGameTensor:
        emtAvg = self.emtAverage()
        wclAvg = self.wclAverage()
        ts = [ma.tensor(emtAvg, wclAvg) for ma in self.analysedMoves]
        ts = ts[:length]
        ts = ts + (length-len(ts))*[AnalysedMove.nullTensor()]
        return ts

    def toJson(self):
        return AnalysedGameBSONHandler.writes(self)

    def emtAverage(self) -> Number:
        return np.average([m.emt for m in self.analysedMoves])

    def wclAverage(self) -> Number:
        return np.average([m.winningChancesLoss() for m in self.analysedMoves])

    def gameLength(self) -> int:
        return len(self.analysedMoves)

    def emts(self) -> List[Emt]:
        return [m.emt for m in self.analysedMoves]

    def emtSeconds(self) -> List[Number]:
        return [emt/100 for emt in self.emts()]

    def winningChances(self) -> List[Number]:
        return [m.advantage() for m in self.analysedMoves]

    def winningChancesPercent(self) -> List[Number]:
        return [100*m.advantage() for m in self.analysedMoves]

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

    def ranks(self) -> List[TrueRank]:
        """ for generating graphs """
        return [move.trueRank() for move in self.analysedMoves]

    def ambiguities(self) -> List[int]:
        """ for generating graphs """
        return [move.ambiguity() for move in self.analysedMoves]

    def length(self) -> int:
        return len(self.analysedMoves)

    def ranksJSON(self) -> str:
        return json.dumps(self.ranks())

    def binnedSeconds(self, bins: int = 10) -> Dict:
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

    def binnedLosses(self, bins: int = 10) -> Dict:
        # JSON format for graphing
        losses = self.winningChancesLossPercent()
        data = [[] for i in range(bins+1)]
        for i in range(0, bins, 1):
            data[min(bins-1,i)] = len([a for a in losses if i == int(a)])
        data[bins] = sum([int(a >= 10) for a in losses])
        labels = [('-' + str(a) + '%') for a in range(bins)]
        labels.append('Other')
        return {'data': json.dumps(data), 'labels': json.dumps(labels)}

    def binnedPVs(self, bins: int = 6) -> Dict:
        # JSON format for graphing
        pvs = self.ranks()
        data = [[] for i in range(bins)]
        for i, p in enumerate([1, 2, 3, 4, 5, None]):
            data[i] = len([1 for pv in pvs if pv == p])
        labels = ['PV 1', 'PV 2', 'PV 3', 'PV 4', 'PV 5', 'Other']
        return {'data': json.dumps(data), 'labels': json.dumps(labels)}

    def moveRankByTime(self) -> List[Dict]:
        return [{'x': time, 'y': rank} for rank, time in zip(self.ranks(), self.emtSeconds())]

    def moveRankByTimeJSON(self) -> str:
        # json format for graphing
        return json.dumps(self.moveRankByTime())

    def lossByTime(self) -> List[Dict]:
        return [{'x': time, 'y': loss} for loss, time in zip(self.winningChancesLossPercent(), self.emtSeconds())]

    def lossByTimeJSON(self) -> str:
        # json format for graphing
        return json.dumps(self.lossByTime())

    def lossByRank(self) -> List[Dict]:
        return [{'x': rank, 'y': loss} for loss, rank in zip(self.winningChancesLossPercent(), self.ranks())]

    def lossByRankJSON(self) -> str:
        # json format for graphing
        return json.dumps(self.lossByRank())

def round_sig(x, sig=2):
    if x == 0:
        return 0
    return round(x, sig-int(floor(log10(abs(x))))-1)

class GameAnalysedGame(NamedTuple('GameAnalysedGame', [
        ('analysedGame', AnalysedGame),
        ('game', Game)
    ])):
    """
    Merger of Game and Analysed Game for a merged tensor
    """
    def length(self):
        return self.analysedGame.length()

    def tensor(self):
        try:
            gt = self.game.boardTensorsByPlayerId(self.analysedGame.playerId, safe = False)
            at = self.analysedGame.tensor()
            return [
                [_1 + _2 for _1, _2 in zip(gt[0], at)],
                gt[1]
            ]
        except (TypeError, AttributeError):
            return None

class AnalysedGameBSONHandler:
    @staticmethod
    def reads(bson: Dict) -> AnalysedGame:
        return AnalysedGame(
            id = bson['_id'],
            playerId = bson['userId'],
            gameId = bson['gameId'],
            analysedMoves = [AnalysedMoveBSONHandler.reads(am) for am in bson['analysis']])

    @staticmethod
    def writes(analysedGame: AnalysedGame) -> Dict:
        return {
            '_id': analysedGame.id,
            'userId': analysedGame.playerId,
            'gameId': analysedGame.gameId,
            'analysis': [AnalysedMoveBSONHandler.writes(am) for am in analysedGame.analysedMoves]
        }

class AnalysedGameDB(NamedTuple('AnalysedGameDB', [
        ('analysedGameColl', Collection)
    ])):
    def write(self, analysedGame: AnalysedGame):
        return self.analysedGameColl.update_one(
            {'_id': analysedGame.id},
            {'$set': AnalysedGameBSONHandler.writes(analysedGame)},
            upsert=True)

    def writeMany(self, analysedGames: List[AnalysedGame]):
        return [self.write(ga) for ga in analysedGames]

    def byPlayerId(self, playerId: PlayerID) -> List[AnalysedGame]:
        return [AnalysedGameBSONHandler.reads(ga) for ga in self.analysedGameColl.find({'userId': playerId})]

    def byPlayerIds(self, playerIds: List[PlayerID]) -> List[AnalysedGame]:
        return [self.byPlayerId(playerId) for playerId in playerIds]

    def byId(self, _id: AnalysedGameID) -> Opt[AnalysedGame]:
        bson = self.analysedGameColl.find_one({"_id": _id})
        return None if bson is None else AnalysedGameBSONHandler.reads(bson)

    def byIds(self, ids: List[AnalysedGameID]) -> List[AnalysedGame]:
        return [AnalysedGameBSONHandler.reads(ga) for ga in self.analysedGameColl.find({"_id": {"$in": ids}})]

    def allBatch(self, batch: int, batchSize: int = 500):
        """
        Gets all analysed games in a paged format
        batch = page number
        batchSize = size of page
        """
        return [AnalysedGameBSONHandler.reads(ga) for ga in self.analysedGameColl.find(skip=batch*batchSize, limit=batchSize)]

    def byGameIdAndUserId(self, gameId: GameID, playerId: PlayerID) -> Opt[AnalysedGame]:
        bson = self.analysedGameColl.find_one({'gameId': gameId, 'userId': playerId})
        return None if bson is None else AnalysedGameBSONHandler.reads(bson)