from collections import namedtuple
from modules.core.MoveAnalysis import AnalysisBSONHandler
import chess.polyglot
import pymongo
import logging

class PositionAnalysis(namedtuple('PositionAnalysis', ['id', 'analyses'])):
    @staticmethod
    def fromBoardAndAnalyses(board, analyses):
        return PositionAnalysis(
            id=PositionAnalysis.idFromBoard(board),
            analyses=analyses)

    @staticmethod
    def idFromBoard(board):
        return str(chess.polyglot.zobrist_hash(board))

class PositionAnalysisBSONHandler:
    @staticmethod
    def reads(bson):
        return PositionAnalysis(
            id=bson['_id'],
            analyses=[AnalysisBSONHandler.reads(b) for b in bson['analyses']])

    def writes(positionAnalysis):
        return {
            '_id': positionAnalysis.id,
            'analyses': [AnalysisBSONHandler.writes(a) for a in positionAnalysis.analyses]
        }

class PositionAnalysisDB(namedtuple('PositionAnalysisDB', ['positionAnalysisColl'])):
    def write(self, positionAnalysis):
        try:
            self.positionAnalysisColl.update_one(
                {'_id': positionAnalysis.id},
                {'$set': PositionAnalysisBSONHandler.writes(positionAnalysis)},
                upsert=True)
        except pymongo.errors.DuplicateKeyError:
            logging.warning("DuplicateKeyError when attempting to write position: " + str(positionAnalysis.id))

    def lazyWriteMany(self, positionAnalyses):
        [self.write(positionAnalysis) for positionAnalysis in positionAnalyses]

    def byBoard(self, board):
        positionAnalysisBSON = self.positionAnalysisColl.find_one({'_id': PositionAnalysis.idFromBoard(board)})
        return None if positionAnalysisBSON is None else PositionAnalysisBSONHandler.reads(positionAnalysisBSON)