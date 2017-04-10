from modules.AnalysedMove import AnalysedMove
import chess
import StringIO
import logging
from math import floor

from modules.bcolors.bcolors import bcolors
from modules.Game import JSONToGame
from modules.PlayerAssessment import PlayerAssessment
from modules.AnalysedMove import JSONToAnalysedMove

class GameAnalysis:
  def __init__(self, game, playerAssessment, analysedMoves = []):
    try:
      from StringIO import StringIO
    except ImportError:
      from io import StringIO
    self.game = game
    self.playerAssessment = playerAssessment
    self.analysedMoves = analysedMoves # List[AnalysedMove]
    
    if len(self.analysedMoves) > 0:
      self.analysed = True
    else:
      self.analysed = False

    self.playableGame = chess.pgn.read_game(StringIO(game.pgn))
    
  def __str__(self):
    if self.analysed:
      return str(self.game) + "\n" + str(self.playerAssessment) + "\n" + str(list([str(am) for am in self.analysedMoves]))
    else:
      return str(self.game) + "\n" + str(self.playerAssessment)

  def json(self):
    return {'game': game.json(),
      'playerAssessment': playerAssessment.json,
      'analysedMoves': list([am.json() for am in self.analysedMoves])}

  def ply(self, moveNumber, white):
    return (2*(moveNumber-1)) + (0 if white else 1)

  def analyse(self, engine, infoHandler, override = False):
    if not self.analysed and not override:
      node = self.playableGame

      logging.debug(bcolors.WARNING + "Game ID: " + self.gameId() + bcolors.ENDC)
      logging.debug(bcolors.OKGREEN + "Game Length: " + str(node.end().board().fullmove_number))
      logging.debug("Analysing Game..." + bcolors.ENDC)

      engine.ucinewgame()

      analysed_positions = []

      logging.debug("Player is white? " + str(self.game.white))
      while not node.is_end():
        nextNode = node.variation(0)
        logging.debug("Analysing move: " + node.variation(0).move.uci())
        if self.game.white == node.board().turn:
          engine.position(node.board())
          engine.go(nodes=5000000)

          analysis = list([{'uci': pv[1][0].uci(), 'score': {'cp': score[1].cp, 'mate': score[1].mate}} for score, pv in zip(infoHandler.info['score'].items(), infoHandler.info['pv'].items())])
          moveNumber = node.board().fullmove_number

          am = AnalysedMove(node.variation(0).move.uci(), moveNumber, analysis, self.game.getEmt(self.ply(moveNumber, self.game.white)))
          logging.debug("Analysis: " + str(am.json()))
          self.analysedMoves.append(am)

        node = nextNode

      self.analysed = True
    return self.analysedMoves

  def userId(self):
    return self.playerAssessment.userId

  def gameId(self):
    return self.game.id

class GameAnalyses:
  def __init__(self, gameAnalyses):
    self.gameAnalyses = gameAnalyses # List[GameAnalysis]

  def byGameId(self, gameId):
    return next(iter([p for p in self.gameAnalyses if p.gameId == gameId]), None)

  def append(self, gameAnalysis):
    return self.gameAnalyses.append(gameAnalysis)

def JSONToGameAnalysis(json):
  return GameAnalysis(JSONToGame(json['game']), PlayerAssessment(json['playerAssessment']), list([JSONToAnalysedMove(am) for am in json['analysedMoves']]))

class GameAnalysisDB:
  def __init__(self, gameAnalysisColl):
    self.gameAnalysisColl = gameAnalysisColl

  def write(self, gameAnalysis):
    self.gameAnalysisColl.update_one({'_id': gameAnalysis.gameId()}, {'$set': {gameAnalysis.json()}}, upsert=True)

  def byUserId(self, userId):
    return GameAnalyses(list([JSONToGameAnalysis(ga) for ga in self.gameAnalysisColl.find({'userId': userId})]))