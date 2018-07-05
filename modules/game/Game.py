from modules.game.Blurs import Blurs, BlursBSONHandler
from modules.game.EngineEval import EngineEval, EngineEvalBSONHandler

from collections import namedtuple
import math
import numpy as np

class Game(namedtuple('Game', ['id', 'white', 'black', 'pgn', 'emts', 'whiteBlurs', 'blackBlurs', 'analysis'])):
    @staticmethod
    def fromDict(gid, userId, d):
        pgn = d['pgn'].split(" ")
        white, black = None, None
        if d['color'] == 'white':
            white = userId
        else:
            black = userId
        return Game(
            id = gid,
            white = white,
            black = black,
            pgn = pgn,
            emts = d.get('emts'),
            whiteBlurs = Blurs.fromDict(d['blurs']['white'], math.ceil(len(pgn)/2)),
            blackBlurs = Blurs.fromDict(d['blurs']['black'], math.floor(len(pgn)/2)),
            analysis = [EngineEval.fromDict(a) for a in d.get('analysis', []) if a is not None]
        )

    @staticmethod
    def fromPlayerData(playerData):
        """Returns a list of Game items from playerData json object from lichess api"""
        return [Game.fromDict(gid, playerData['user']['id'], g) for gid, g in playerData['games'].items() \
                 if g.get('initialFen') is None and g.get('variant') is None]

    def tensor(self, userId):
        if self.analysis == [] or self.emts is None and (self.white == userId or self.black == userId):
            return None

        white = (self.white == userId)
        blurs = self.whiteBlurs.moves if white else self.blackBlurs.moves

        analysis = self.analysis[1:] if white else self.analysis
        analysis = list(zip(analysis[0::2],analysis[1::2]))

        emts = self.emtsByColour(white)
        avgEmt = np.average(emts)
        tensors = [Game.moveTensor(a, b, e, avgEmt, white) for a, b, e in zip(analysis, blurs, emts)]
        tensors = (max(0, 100-len(tensors)))*[Game.nullTensor()] + tensors
        return tensors[:100]

    def emtsByColour(self, white):
        return self.emts[(0 if white else 1)::2]

    @staticmethod
    def moveTensor(analysis, blur, emt, avgEmt, white):
        return [
            analysis[1].winningChances(white),
            (analysis[0].winningChances(white) - analysis[1].winningChances(white)),
            int(blur),
            emt,
            emt - avgEmt,
            100*((emt - avgEmt)/(avgEmt + 1e-8)),
        ]

    @staticmethod
    def nullTensor():
        return [0, 0, 0, 0, 0, 0]

    @staticmethod
    def ply(moveNumber, white):
        return (2*(moveNumber-1)) + (0 if white else 1)

    def getBlur(self, white, moveNumber):
        if white:
            return self.whiteBlurs.moves[moveNumber-1]
        return self.blackBlurs.moves[moveNumber-1]

class GameBSONHandler:
    @staticmethod
    def reads(bson):
        return Game(
            id = bson['_id'],
            white = bson.get('white'),
            black = bson.get('black'),
            pgn = bson['pgn'],
            emts = bson['emts'],
            whiteBlurs = BlursBSONHandler.reads(bson['whiteBlurs']),
            blackBlurs = BlursBSONHandler.reads(bson['blackBlurs']),
            analysis = EngineEvalBSONHandler.reads(bson.get('analysis', [])))

    @staticmethod
    def writes(game):
        return {
            '_id': game.id,
            'white': game.white,
            'black': game.black,
            'pgn': game.pgn,
            'emts': game.emts,
            'whiteBlurs': BlursBSONHandler.writes(game.whiteBlurs),
            'blackBlurs': BlursBSONHandler.writes(game.blackBlurs),
            'analysis': EngineEvalBSONHandler.writes(game.analysis),
            'analysed': len(game.analysis) > 0
        }

class GameDB(namedtuple('GameDB', ['gameColl'])):
    def byId(self, _id):
        return GameBSONHandler.reads(self.gameColl.find_one({'_id': _id}))

    def byIds(self, ids): # List[Ids]
        return list([GameBSONHandler.reads(g) for g in self.gameColl.find({'_id': {'$in': [i for i in ids]}})])

    def byUserId(self, uid):
        return list([GameBSONHandler.reads(g) for g in self.gameColl.find({"$or": [{"white": uid}, {"black": uid}]})])

    def byUserIdAnalysed(self, uid):
        return list([GameBSONHandler.reads(g) for g in self.gameColl.find({"analysed": True, "$or": [{"white": uid}, {"black": uid}]})])

    def write(self, game): # Game
        self.gameColl.update_one({'_id': game.id}, {'$set': GameBSONHandler.writes(game)}, upsert=True)

    def lazyWriteGames(self, games):
        [self.write(g) for g in games]