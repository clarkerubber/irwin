from modules.AnalysedMove import AnalysedMove
import chess
import chess.pgn
import logging

from modules.bcolors.bcolors import bcolors
from modules.PlayerAssessment import PlayerAssessment

from modules.Game import GameBSONHandler
from modules.AnalysedMove import AnalysedMoveBSONHandler

class GameAnalysis:
  def __init__(self, game, playerAssessment, analysedMoves):
    try:
      from StringIO import StringIO
    except ImportError:
      from io import StringIO
    self.id = gameAnalysisId(game.id, playerAssessment.white) # gameId/colour
    self.gameId = game.id
    self.userId = playerAssessment.userId
    self.game = game
    self.playerAssessment = playerAssessment
    self.analysedMoves = analysedMoves # List[AnalysedMove]
    self.white = self.playerAssessment.white
    self.analysed = len(self.analysedMoves) > 0

    self.playableGame = chess.pgn.read_game(StringIO(game.pgn))
    
  def __str__(self):
    if self.analysed:
      return str(self.game) + "\n" + str(self.playerAssessment) + "\n" + str([str(am) for am in self.analysedMoves])
    else:
      return str(self.game) + "\n" + str(self.playerAssessment)

  def ply(self, moveNumber, white):
    return (2*(moveNumber-1)) + (0 if white else 1)

def gameAnalysisId(gameId, white):
  return gameId + '/' + ('white' if white else 'black')

def analyse(gameAnalysis, engine, infoHandler, override = False):
  if not gameAnalysis.analysed or override:
    node = gameAnalysis.playableGame

    logging.debug(bcolors.WARNING + "Game ID: " + gameAnalysis.gameId + bcolors.ENDC)
    logging.debug(bcolors.OKGREEN + "Game Length: " + str(node.end().board().fullmove_number))
    logging.debug("Analysing Game..." + bcolors.ENDC)

    engine.ucinewgame()

    analysed_positions = []

    while not node.is_end():
      nextNode = node.variation(0)
      if gameAnalysis.white == node.board().turn:
        engine.position(node.board())
        engine.go(nodes=5000000)

        analysis = list([{'uci': pv[1][0].uci(), 'score': {'cp': score[1].cp, 'mate': score[1].mate}} for score, pv in zip(infoHandler.info['score'].items(), infoHandler.info['pv'].items())])
        moveNumber = node.board().fullmove_number

        am = AnalysedMove(node.variation(0).move.uci(), moveNumber, analysis, gameAnalysis.game.getEmt(gameAnalysis.ply(moveNumber, gameAnalysis.white)))
        gameAnalysis.analysedMoves.append(am)

      node = nextNode

    gameAnalysis.analysed = True
  return gameAnalysis

class GameAnalyses:
  def __init__(self, gameAnalyses):
    self.gameAnalyses = gameAnalyses # List[GameAnalysis]

  def byGameId(self, gameId):
    return next([p for p in self.gameAnalyses if p.gameId == gameId], None)

  def append(self, gameAnalysis):
    if not self.hasId(gameAnalysis.id):
      self.gameAnalyses.append(gameAnalysis)

  def analyse(self, engine, infoHandler):
    self.gameAnalyses = [analyse(ga, engine, infoHandler) for ga in self.gameAnalyses]

  def ids(self):
    return list([ga.id for ga in self.gameAnalyses])

  def hasId(self, _id):
    return (_id in self.ids())

class GameAnalysisBSONHandler:
  @staticmethod
  def reads(game, playerAssessment, analysedMovesBSON):
    return GameAnalysis(game, playerAssessment, [AnalysedMoveBSONHandler.reads(am) for am in analysedMovesBSON])

  @staticmethod
  def writes(gameAnalysis):
    return {
      '_id': gameAnalysis.id,
      'gameId': gameAnalysis.gameId,
      'userId': gameAnalysis.userId,
      'analysedMoves': list([AnalysedMoveBSONHandler.writes(am) for am in gameAnalysis.analysedMoves])
    }

class GameAnalysisDB:
  def __init__(self, gameAnalysisColl, gameDB, playerAssessmentDB):
    self.gameAnalysisColl = gameAnalysisColl
    self.gameDB = gameDB
    self.playerAssessmentDB = playerAssessmentDB

  def write(self, gameAnalysis):
    self.gameAnalysisColl.update_one({'_id': gameAnalysis.id}, {'$set': GameAnalysisBSONHandler.writes(gameAnalysis)}, upsert=True)

  def byUserId(self, userId):
    playerAssessments = self.playerAssessmentDB.byUserId(userId)
    games = self.gameDB.byIds(playerAssessments.gameIds())
    gameAnalysisJSONs = self.gameAnalysisColl.find({'userId': userId})

    gameAnalyses = GameAnalyses([])
    for ga in gameAnalysisJSONs:
      if games.hasId(ga['gameId']) and playerAssessments.hasGameId(ga['gameId']):
        gameAnalyses.append(GameAnalysisBSONHandler.reads(
          games.byId(ga['gameId']),
          playerAssessments.byGameId(ga['gameId']),
          ga['analysedMoves']))
    return gameAnalyses

  def lazyWriteGames(self, gameAnalyses):
    [self.write(ga) for ga in gameAnalyses.gameAnalyses]