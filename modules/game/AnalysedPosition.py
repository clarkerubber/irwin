from collections import namedtuple
from modules.game.AnalysedMove import AnalysisBSONHandler
import chess.polyglot
import pymongo
import logging

class AnalysedPosition(namedtuple('AnalysedPosition', ['id', 'analyses'])):
    """
    Like an analysed move, but only with SF analysis. Does not contain any other move data.
    This is used for accelerating stockfish analysis.
    """
    @staticmethod
    def fromBoardAndAnalyses(board, analyses):
        return AnalysedPosition(
            id=AnalysedPosition.idFromBoard(board),
            analyses=analyses)

    @staticmethod
    def idFromBoard(board):
        return str(chess.polyglot.zobrist_hash(board))

class AnalysedPositionBSONHandler:
    @staticmethod
    def reads(bson):
        return AnalysedPosition(
            id=bson['_id'],
            analyses=[AnalysisBSONHandler.reads(b) for b in bson['analyses']])

    def writes(analysedPosition):
        return {
            '_id': analysedPosition.id,
            'analyses': [AnalysisBSONHandler.writes(a) for a in analysedPosition.analyses]
        }

class AnalysedPositionDB(namedtuple('AnalysedPositionDB', ['analysedPositionColl'])):
    def write(self, analysedPosition):
        try:
            self.analysedPositionColl.update_one(
                {'_id': analysedPosition.id},
                {'$set': AnalysedPositionBSONHandler.writes(analysedPosition)},
                upsert=True)
        except pymongo.errors.DuplicateKeyError:
            logging.warning("DuplicateKeyError when attempting to write position: " + str(analysedPosition.id))

    def lazyWriteMany(self, analysedPositions):
        [self.write(analysedPosition) for analysedPosition in analysedPositions]

    def byBoard(self, board):
        analysedPositionBSON = self.analysedPositionColl.find_one({'_id': AnalysedPosition.idFromBoard(board)})
        return None if analysedPositionBSON is None else AnalysedPositionBSONHandler.reads(analysedPositionBSON)