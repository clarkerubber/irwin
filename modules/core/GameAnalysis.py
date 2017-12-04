from chess.pgn import read_game
import logging
import numpy as np

import modules.core.AnalysedMove as AnalysedMove

from collections import namedtuple

class GameAnalysis(namedtuple('GameAnalysis', ['id', 'userId', 'gameId', 'moveAnalyses'])):
  def moveAnalysisTensors(self):
    return [ma.tensor(moveNo, self.emtAverage()) for moveNo, ma in enumerate(self.moveAnalyses)]

  def emtAverage(self):
    return np.average([m.emt for m in self.moveAnalyses])

  @staticmethod
  def gameAnalysisId(gameId, white):
    return gameId + '/' + ('white' if white else 'black')

  @staticmethod
  def ply(moveNumber, white):
    return (2*(moveNumber-1)) + (0 if white else 1)

  @staticmethod
  def fromGame(game, engine, infoHandler, white, nodes, threadId = 0):
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

    logging.debug(str(threadId) + ": " +game.id + " - " + str(node.end().board().fullmove_number) + " moves")

    engine.ucinewgame()

    analysed_positions = []

    while not node.is_end():
      nextNode = node.variation(0)
      if white == node.board().turn:
        engine.setoption({'multipv': 5})
        engine.position(node.board())
        engine.go(nodes=nodes)

        analyses = list([
          AnalysedMove.Analysis(pv[1][0].uci(),
            AnalysedMove.Score(score[1].cp, score[1].mate)) for score, pv in zip(
              infoHandler.info['score'].items(),
              infoHandler.info['pv'].items())])

        engine.setoption({'multipv': 1})
        engine.position(nextNode.board())
        engine.go(nodes=nodes)

        cp = infoHandler.info['score'][1].cp
        mate = infoHandler.info['score'][1].mate

        score = AnalysedMove.Score(-cp if cp is not None else None,
          -mate if mate is not None else None) # flipped because analysing from other player side

        moveNumber = node.board().fullmove_number

        analysis.append(AnalysedMove.AnalysedMove(
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
      moveAnalyses = [AnalysedMove.AnalysedMoveBSONHandler.reads(am) for am in bson['analysis']])

  @staticmethod
  def writes(gameAnalysis):
    return {
      '_id': gameAnalysis.id,
      'userId': gameAnalysis.userId,
      'gameId': gameAnalysis.gameId,
      'analysis': [AnalysedMove.AnalysedMoveBSONHandler.writes(am) for am in gameAnalysis.moveAnalyses]
    }

class GameAnalysisDB(namedtuple('GameAnalysisDB', ['gameAnalysisColl'])):
  def write(self, gameAnalysis):
    self.gameAnalysisColl.update_one({'_id': gameAnalysis.id}, {'$set': GameAnalysisBSONHandler.writes(gameAnalysis)}, upsert=True)

  def byUserId(self, userId):
    return [GameAnalysisBSONHandler.reads(ga) for ga in self.gameAnalysisColl.find({'userId': userId})]

  def byUserIds(self, userIds):
    return [self.byUserId(userId) for userId in userIds]

  def byIds(self, ids):
    return [GameAnalysisBSONHandler.reads(ga) for ga in self.gameAnalysisColl.find({"_id": {"$in": ids}})]

  def lazyWriteGameAnalyses(self, gameAnalyses):
    [self.write(ga) for ga in gameAnalyses]