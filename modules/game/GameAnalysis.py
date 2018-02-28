from chess.pgn import read_game
import logging
import numpy as np

from modules.game.MoveAnalysis import MoveAnalysis, MoveAnalysisBSONHandler, Score, Analysis
from modules.game.PositionAnalysis import PositionAnalysis

from collections import namedtuple

class GameAnalysis(namedtuple('GameAnalysis', ['id', 'userId', 'gameId', 'moveAnalyses'])):
    def moveAnalysisTensors(self, length=60):
        emtAvg = self.emtAverage()
        wclAvg = self.wclAverage()
        ts = [ma.tensor(emtAvg, wclAvg) for ma in self.moveAnalyses]
        ts = ts[:length]
        ts = ts + (length-len(ts))*[MoveAnalysis.nullTensor()]
        return np.array(ts)

    def emtAverage(self):
        return np.average([m.emt for m in self.moveAnalyses])

    def wclAverage(self):
        return np.average([m.winningChancesLoss() for m in self.moveAnalyses])

    def gameLength(self):
        return len(self.moveAnalyses)

    def blurs(self):
        return [move.blur for move in self.moveAnalyses]

    def emts(self):
        return [m.emt for m in self.moveAnalyses]

    def emtSeconds(self):
        return [emt/100 for emt in self.emts()]

    def winningChances(self):
        return [m.advantage() for m in self.moveAnalyses]

    def winningChancesPercent(self):
        return [100*m.advantage() for m in self.moveAnalyses]

    def winningChancesLossPercent(self, usePV=True):
        return [100*m.winningChancesLoss(usePV=usePV) for m in self.moveAnalyses]

    def winningChancesLossByPV(self):
        """ for generating graphs """
        pvs = [(
            'PV'+str(i+1),
            'rgba(20, 20, 20, ' + str(0.6 - i*0.1) + ')',
            []) for i in range(5)] # one entry per PV
        for moveAnalysis in self.moveAnalyses:
            losses = moveAnalysis.PVsWinningChancesLoss()
            for i in range(5):
                try:
                    pvs[i][2].append(max(0, 100*losses[i]))
                except IndexError:
                    pvs[i][2].append('null')
        return pvs

    def ranks(self):
        """ for generating graphs """
        return [('null' if move.trueRank() is None else move.trueRank()) for move in self.moveAnalyses]

    def ambiguities(self):
        """ for generating graphs """
        return [move.ambiguity() for move in self.moveAnalyses]

    def length(self):
        return len(self.moveAnalyses)

    @staticmethod
    def gameAnalysisId(gameId, white):
        return gameId + '/' + ('white' if white else 'black')

    @staticmethod
    def ply(moveNumber, white):
        return (2*(moveNumber-1)) + (0 if white else 1)

    @staticmethod
    def fromGame(game, engine, infoHandler, white, nodes, positionAnalysisDB):
        logging.info("analysing: " + game.id)
        if len(game.pgn) < 40 or len(game.pgn) > 120:
            return None
        analysis = []
        try:
            from StringIO import StringIO
        except ImportError:
            from io import StringIO

        try:
            playableGame = read_game(StringIO(" ".join(game.pgn)))
        except ValueError:
            return None

        node = playableGame

        engine.ucinewgame()

        while not node.is_end():
            nextNode = node.variation(0)
            if white == node.board().turn: ## if it is the turn of the player of interest
                dbCache = positionAnalysisDB.byBoard(node.board())
                if dbCache is not None:
                    analyses = dbCache.analyses
                else:
                    engine.setoption({'multipv': 5})
                    engine.position(node.board())
                    engine.go(nodes=nodes)

                    analyses = list([
                        Analysis(pv[1][0].uci(),
                            Score(score[1].cp, score[1].mate)) for score, pv in zip(
                                infoHandler.info['score'].items(),
                                infoHandler.info['pv'].items())])

                    # write position to DB as it wasn't there before
                    positionAnalysisDB.write(PositionAnalysis.fromBoardAndAnalyses(node.board(), analyses))

                dbCache = positionAnalysisDB.byBoard(nextNode.board())
                if dbCache is not None:
                    score = dbCache.analyses[0].score.inverse()
                else:
                    engine.setoption({'multipv': 1})
                    engine.position(nextNode.board())
                    engine.go(nodes=nodes)

                    score = Score(infoHandler.info['score'][1].cp,
                        infoHandler.info['score'][1].mate).inverse() # flipped because analysing from other player side

                moveNumber = node.board().fullmove_number

                analysis.append(MoveAnalysis(
                    uci = node.variation(0).move.uci(),
                    move = moveNumber,
                    emt = game.emts[GameAnalysis.ply(moveNumber, white)],
                    blur = game.getBlur(white, moveNumber),
                    score = score,
                    analyses = analyses))

            node = nextNode

        userId = game.white if white else game.black
        return GameAnalysis(GameAnalysis.gameAnalysisId(game.id, white), userId, game.id, analysis)

class GameAnalysisBSONHandler:
    @staticmethod
    def reads(bson):
        return GameAnalysis(
            id = bson['_id'],
            userId = bson['userId'],
            gameId = bson['gameId'],
            moveAnalyses = [MoveAnalysisBSONHandler.reads(am) for am in bson['analysis']])

    @staticmethod
    def writes(gameAnalysis):
        return {
            '_id': gameAnalysis.id,
            'userId': gameAnalysis.userId,
            'gameId': gameAnalysis.gameId,
            'analysis': [MoveAnalysisBSONHandler.writes(am) for am in gameAnalysis.moveAnalyses]
        }

class GameAnalysisDB(namedtuple('GameAnalysisDB', ['gameAnalysisColl'])):
    def write(self, gameAnalysis):
        self.gameAnalysisColl.update_one(
            {'_id': gameAnalysis.id},
            {'$set': GameAnalysisBSONHandler.writes(gameAnalysis)},
            upsert=True)

    def lazyWriteGameAnalyses(self, gameAnalyses):
        [self.write(ga) for ga in gameAnalyses]

    def byUserId(self, userId):
        return [GameAnalysisBSONHandler.reads(ga) for ga in self.gameAnalysisColl.find({'userId': userId})]

    def byUserIds(self, userIds):
        return [self.byUserId(userId) for userId in userIds]

    def byIds(self, ids):
        return [GameAnalysisBSONHandler.reads(ga) for ga in self.gameAnalysisColl.find({"_id": {"$in": ids}})]

    def allBatch(self, batch, batchSize=500):
        return [GameAnalysisBSONHandler.reads(ga) for ga in self.gameAnalysisColl.find(skip=batch*batchSize, limit=batchSize)]

    def byGameIdAndUserId(self, gameId, userId):
        bson = self.gameAnalysisColl.find_one({'gameId': gameId, 'userId': userId})
        return None if bson is None else GameAnalysisBSONHandler.reads(bson)