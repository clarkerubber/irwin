import chess
import chess.pgn
import logging

from modules.bcolors.bcolors import bcolors

from modules.core.PlayerAssessment import PlayerAssessment
from modules.core.AnalysedMove import AnalysedMove, Analysis, Score
from modules.core.Game import GameBSONHandler
from modules.core.GameAnalyses import GameAnalyses
from modules.core.AnalysedMove import AnalysedMoveBSONHandler
from modules.core.AssessedMove import AssessedMoveBSONHandler

from collections import namedtuple

class GameAnalysis:
  def __init__(self, game, playerAssessment, analysedMoves, assessedMoves):
    try:
      from StringIO import StringIO
    except ImportError:
      from io import StringIO

    self.id = gameAnalysisId(game.id, playerAssessment.white) # gameId/colour
    self.gameId = game.id
    self.userId = playerAssessment.userId
    self.game = game
    self.playerAssessment = playerAssessment

    self.analysedMoves = analysedMoves # List[AnalysedMove] (Analysed by Stockfish)
    self.assessedMoves = assessedMoves # List[AssessedMove] (Assessed by Irwin/TensorFlow)
    
    self.analysed = len(self.analysedMoves) > 0
    self.assessed = len(self.assessedMoves) > 0

    self.playableGame = chess.pgn.read_game(StringIO(game.pgn))
    self.white = self.playerAssessment.white
    
  def __str__(self):
    return str(self.game) + "\n" + str(self.playerAssessment) + "\n" + str([str(am) for am in self.analysedMoves])

  def movesForAssessment(self): # Moves where the played move is not in top 5
    return [am for am in self.analysedMoves if am.inTopFive()]
  
  def completeMovesForAssessment(self): # Moves where the played move is in top 5 (has complete information)
    pass

  def ply(self, moveNumber, white):
    return (2*(moveNumber-1)) + (0 if white else 1)

def gameAnalysisId(gameId, white):
  return gameId + '/' + ('white' if white else 'black')

class GameAnalysisBSONHandler:
  @staticmethod
  def reads(game, playerAssessment, analysedMovesBSON, assessedMovesBSON):
    return GameAnalysis(
      game,
      playerAssessment,
      [AnalysedMoveBSONHandler.reads(am) for am in analysedMovesBSON],
      [AssessedMoveBSONHandler.reads(am) for am in assessedMovesBSON])

  @staticmethod
  def writes(gameAnalysis):
    return {
      '_id': gameAnalysis.id,
      'gameId': gameAnalysis.gameId,
      'userId': gameAnalysis.userId,
      'analysedMoves': [AnalysedMoveBSONHandler.writes(am) for am in gameAnalysis.analysedMoves],
      'assessedMoves': [AssessedMoveBSONHandler.writes(am) for am in gameAnalysis.assessedMoves]
    }

class GameAnalysisDB(namedtuple('GameAnalysisDB', ['gameAnalysisColl', 'gameDB', 'playerAssessmentDB'])):
  def write(self, gameAnalysis):
    self.gameAnalysisColl.update_one({'_id': gameAnalysis.id}, {'$set': GameAnalysisBSONHandler.writes(gameAnalysis)}, upsert=True)

  def byUserId(self, userId):
    playerAssessments = self.playerAssessmentDB.byUserId(userId)
    games = self.gameDB.byIds(playerAssessments.gameIds())
    gameAnalysisBSONs = self.gameAnalysisColl.find({'userId': userId})

    gameAnalyses = GameAnalyses([])
    for ga in gameAnalysisBSONs:
      if games.hasId(ga['gameId']) and playerAssessments.hasGameId(ga['gameId']):
        gameAnalyses.append(GameAnalysisBSONHandler.reads(
          games.byId(ga['gameId']),
          playerAssessments.byGameId(ga['gameId']),
          ga['analysedMoves'],
          ga['assessedMoves']))
    return gameAnalyses

  def byUserIds(self, userIds):
    return [self.byUserId(userId) for userId in userIds]

  def lazyWriteGames(self, gameAnalyses):
    [self.write(ga) for ga in gameAnalyses.gameAnalyses]