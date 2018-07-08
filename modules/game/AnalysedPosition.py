from default_imports import *

from modules.game.AnalysedMove import Analysis, AnalysisBSONHandler
from chess import polyglot, Board
from pymongo.collection import Collection
import pymongo
import logging

AnalysedPositionID = NewType('AnalysedPositionID', str)

class AnalysedPosition(NamedTuple('AnalysedPosition', [
        ('id', AnalysedPositionID),
        ('analyses', List[Analysis])
    ])):
    """
    Like an analysed move, but only with SF analysis. Does not contain any other move data.
    This is used for accelerating stockfish analysis.
    """
    @staticmethod
    def fromBoardAndAnalyses(board: Board, analyses: List[Analysis]):
        return AnalysedPosition(
            id=AnalysedPosition.idFromBoard(board),
            analyses=analyses)

    @staticmethod
    def idFromBoard(board: Board) -> AnalysedPositionID:
        return str(polyglot.zobrist_hash(board))

class AnalysedPositionBSONHandler:
    @staticmethod
    def reads(bson: Dict) -> AnalysedPosition:
        return AnalysedPosition(
            id=bson['_id'],
            analyses=[AnalysisBSONHandler.reads(b) for b in bson['analyses']])

    def writes(analysedPosition: AnalysedPosition) -> Dict:
        return {
            '_id': analysedPosition.id,
            'analyses': [AnalysisBSONHandler.writes(a) for a in analysedPosition.analyses]
        }

class AnalysedPositionDB(NamedTuple('AnalysedPositionDB', [
        ('analysedPositionColl', Collection)
    ])):
    def write(self, analysedPosition: AnalysedPosition):
        try:
            self.analysedPositionColl.update_one(
                {'_id': analysedPosition.id},
                {'$set': AnalysedPositionBSONHandler.writes(analysedPosition)},
                upsert=True)
        except pymongo.errors.DuplicateKeyError:
            logging.warning("DuplicateKeyError when attempting to write position: " + str(analysedPosition.id))

    def lazyWriteMany(self, analysedPositions: List[AnalysedPosition]):
        [self.write(analysedPosition) for analysedPosition in analysedPositions]

    def byBoard(self, board: Board) -> Opt[AnalysedPosition]:
        analysedPositionBSON = self.analysedPositionColl.find_one({'_id': AnalysedPosition.idFromBoard(board)})
        return None if analysedPositionBSON is None else AnalysedPositionBSONHandler.reads(analysedPositionBSON)