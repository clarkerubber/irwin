from default_imports import *

from modules.game.Colour import Colour
from modules.game.Player import PlayerID
from modules.game.EngineEval import EngineEval, EngineEvalBSONHandler

from pymongo.collection import Collection

from multiprocessing import Pool

import math
import chess
from chess.pgn import read_game
import numpy as np

GameID = NewType('GameID', str)
Emt = NewType('Emt', int)
Analysis = NewType('Analysis', Opt[List[EngineEval]])

MoveTensor = NewType('MoveTensor', List[Number])
GameTensor = NewType('GameTensor', List[MoveTensor])

class Game(NamedTuple('Game', [
        ('id', GameID),
        ('white', PlayerID),
        ('black', PlayerID),
        ('pgn', List[str]),
        ('emts', Opt[List[Emt]]),
        ('analysis', Analysis)
    ])):
    @staticmethod
    def fromDict(d: Dict):
        return Game(
            id=d['id'],
            white=d['white'],
            black=d['black'],
            pgn=d['pgn'].split(' '),
            emts=d['emts'],
            analysis=None if d.get('analysis') is None else [EngineEval.fromDict(a) for a in d['analysis']]
            )

    @staticmethod
    def fromJson(json: Dict):
        return Game.fromDict(json)

    def playable(self):
        try:
            from StringIO import StringIO
        except ImportError:
            from io import StringIO

        return read_game(StringIO(" ".join(self.pgn)))

    def boardTensors(self, colour):
        # replay the game for move tensors
        playable = self.playable()
        node = playable.variation(0)

        advancement = lambda rank: rank if colour else (7 - rank)

        while not node.is_end():
            nextNode = node.variation(0)

            board = node.board()
            move = node.move

            if board.turn == colour:
                yield (
                    [
                        advancement(chess.square_rank(move.to_square)),
                        board.pseudo_legal_moves.count(),
                        int(board.is_capture(move))
                    ],
                    board.piece_at(move.to_square).piece_type
                )

            node = nextNode

    def boardTensorsByPlayerId(self, playerId: PlayerID, length: int = 60, safe: bool = True):
        if safe and self.white != playerId and self.black != playerId:
            logging.warning(f'{playerId} is not a player in game {self.id} - ({self.white}, {self.black})')
            return None

        colour = (self.white == playerId)
        tensors = list(self.boardTensors(colour))
        remaining = max(0, length-len(tensors))
        output = [
            [remaining*[Game.nullBoardTensor()] + [t[0] for t in tensors]][0][:length],
            [remaining*[[0]] + [[t[1]] for t in tensors]][0][:length]
        ]

        return output

    def tensor(self, playerId: PlayerID, length: int = 60, noisey: bool = False, safe: bool = True) -> Opt[GameTensor]:
        if self.analysis == [] or (safe and self.white != playerId and self.black != playerId):
            if noisey:
                logging.debug(f'playerId: "{playerId}"')
                logging.debug(f'gameId: "{self.id}"')
                logging.debug(f'white: "{self.white}"')
                logging.debug(f'black: "{self.black}"')
            return None

        colour = (self.white == playerId)

        analysis = self.analysis[1:] if colour else self.analysis
        analysis = list(zip(analysis[0::2],analysis[1::2])) # grouping analyses pairwise

        emts = self.emtsByColour(colour, [-1 for _ in self.analysis] if self.emts is None else self.emts)
        avgEmt = np.average(emts)
        boardTensors = list(self.boardTensors(colour))
        pieceTypes = [[b[1]] for b in boardTensors]
        tensors = [Game.moveTensor(a, e, b, avgEmt, colour) for a, e, b in zip(analysis, emts, [b[0] for b in boardTensors])]
        remaining = (max(0, length-len(tensors)))
        tensors = [
                #np.array([remaining*[Game.nullMoveTensor()] + tensors][0][:length]),
                [remaining*[Game.nullMoveTensor()] + tensors][0][:length],
                #np.array([remaining*[[0]] + pieceTypes][0][:length])
                [remaining*[[0]] + pieceTypes][0][:length]
            ] # pad to `length` tensors in length
        return tensors

    def emtsByColour(self, colour: Colour, emts: Opt[List[int]] = None) -> List[Emt]:
        emts = self.emts if emts is None else emts
        return emts[(0 if colour else 1)::2]

    @staticmethod
    def moveTensor(analysis: Analysis, emt: Emt, boardTensor: List[int], avgEmt: Number, colour: Colour) -> MoveTensor:
        return [
            analysis[1].winningChances(colour),
            (analysis[0].winningChances(colour) - analysis[1].winningChances(colour)),
            emt,
            emt - avgEmt,
            100*((emt - avgEmt)/(avgEmt + 1e-8)),
        ] + boardTensor

    @staticmethod
    def nullBoardTensor():
        return [0, 0, 0]

    @staticmethod
    def nullMoveTensor() -> MoveTensor:
        return [0, 0, 0, 0, 0, 0, 0, 0]

    @staticmethod
    def ply(moveNumber: int, colour: Colour) -> int:
        return (2*(moveNumber-1)) + (0 if colour else 1)

class GameBSONHandler:
    @staticmethod
    def reads(bson: Dict) -> Game:
        return Game(
            id = bson['_id'],
            white = bson.get('white'),
            black = bson.get('black'),
            pgn = bson['pgn'],
            emts = bson['emts'],
            analysis = [EngineEvalBSONHandler.reads(a) for a in bson.get('analysis', [])])

    @staticmethod
    def writes(game: Game) -> Dict:
        return {
            '_id': game.id,
            'white': game.white,
            'black': game.black,
            'pgn': game.pgn,
            'emts': game.emts,
            'analysis': [EngineEvalBSONHandler.writes(a) for a in game.analysis],
            'analysed': len(game.analysis) > 0
        }

class GameDB(NamedTuple('GameDB', [
        ('gameColl', Collection)
    ])):
    def byId(self, _id: GameID) -> Opt[Game]:
        bson = self.gameColl.find_one({'_id': _id})
        return None if bson is None else GameBSONHandler.reads(bson)

    def byIds(self, ids: List[GameID]) -> List[Game]:
        return [self.byId(gid) for gid in ids]
        #return [GameBSONHandler.reads(g) for g in self.gameColl.find({'_id': {'$in': [i for i in ids]}})]

    def byPlayerId(self, playerId: PlayerID) -> List[Game]:
        return [GameBSONHandler.reads(g) for g in self.gameColl.find({"$or": [{"white": playerId}, {"black": playerId}]})]

    def byPlayerIdAndAnalysed(self, playerId: PlayerID, analysed: bool = True) -> List[Game]:
        return [GameBSONHandler.reads(g) for g in self.gameColl.find({"analysed": analysed, "$or": [{"white": playerId}, {"black": playerId}]})]

    def write(self, game: Game):
        self.gameColl.update_one({'_id': game.id}, {'$set': GameBSONHandler.writes(game)}, upsert=True)

    def writeMany(self, games: List[Game]):
        [self.write(g) for g in games]