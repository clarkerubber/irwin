import chess
import chess.pgn
import logging
import numpy

from modules.bcolors.bcolors import bcolors

from modules.core.PlayerAssessment import PlayerAssessment
from modules.core.AnalysedMove import AnalysedMove, Analysis, Score
from modules.core.Game import GameBSONHandler
from modules.core.GameAnalyses import GameAnalyses
from modules.core.AnalysedMove import AnalysedMoveBSONHandler
from modules.core.AssessedMove import AssessedMoveBSONHandler
from modules.core.AssessedChunk import AssessedChunkBSONHandler

from collections import namedtuple

class GameAnalysis:
  def __init__(self, game, playerAssessment, analysedMoves, assessedMoves, assessedChunks):
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
    self.assessedChunks = assessedChunks # List[AssessedChunk] (groups of 10 moves assessed by Irwin/TensorFlow)
    
    self.analysed = len(self.analysedMoves) > 0
    self.assessed = len(self.assessedMoves) > 0

    self.playableGame = chess.pgn.read_game(StringIO(game.pgn))
    self.white = self.playerAssessment.white

  def rankedMoves(self): # Moves where the played move is in top 5
    return [am for am in self.analysedMoves if am.inAnalyses()]

  def ply(self, moveNumber):
    return (2*(moveNumber-1)) + (0 if self.white else 1)

  def consistentMoveTime(self, moveNumber):
    return self.game.emts[self.ply(moveNumber)] in self.game.emtsNoOutliers()

  def tensorInputChunks(self, titled):
    entries = []
    for i in range(len(self.analysedMoves) - 9):
      entry = [
        int(titled),
        int(self.playerAssessment.hold),
        int(self.playerAssessment.blurs),
        i]
      for analysedMove in self.analysedMoves[i:i+10]:
        entry.extend([analysedMove.rank(),
        int(100*analysedMove.winningChancesLoss()),
        int(100*analysedMove.advantage()),
        analysedMove.ambiguity(),
        int(self.consistentMoveTime(analysedMove.move))])
      entries.append(entry)
    return entries

  def tensorInputMoves(self, titled):
    return [[
      int(titled),
      analysedMove.move,
      analysedMove.rank(),
      int(100*analysedMove.winningChancesLoss()),
      int(100*analysedMove.advantage()),
      analysedMove.ambiguity(),
      int(self.consistentMoveTime(analysedMove.move)),
      int(self.playerAssessment.hold),
      self.playerAssessment.blurs] for analysedMove in self.analysedMoves]

  @staticmethod
  def averageChunks(assessedChunks):
    return numpy.mean([chunk.irwinReport.activation for chunk in assessedChunks])

  def normalisedAssessedMoves(self):
    if self.assessed: # bear with me here. Average of the move (50%) and all the chunks that cover it (50%).
      return [numpy.mean([
          assessedMove.irwinReport.activation,
          GameAnalysis.averageChunks(self.assessedChunks[max(0,assessedMove.analysedMove.move-10):min(len(self.assessedChunks),assessedMove.analysedMove.move)])
        ]) for assessedMove in self.assessedMoves]
    return []

  def assessmentOutlierAverage(self):
    norm = sorted(self.normalisedAssessedMoves())
    return numpy.mean(norm[-int(0.2*len(norm)):])

  def assessmentAverage(self):
    return numpy.mean(self.normalisedAssessedMoves())


def gameAnalysisId(gameId, white):
  return gameId + '/' + ('white' if white else 'black')

class GameAnalysisBSONHandler:
  @staticmethod
  def reads(game, playerAssessment, analysedMovesBSON, assessedMovesBSON, assessedChunksBSON):
    return GameAnalysis(
      game,
      playerAssessment,
      [AnalysedMoveBSONHandler.reads(am) for am in analysedMovesBSON],
      [AssessedMoveBSONHandler.reads(am) for am in assessedMovesBSON],
      [AssessedChunkBSONHandler.reads(ac) for ac in assessedChunksBSON])

  @staticmethod
  def writes(gameAnalysis):
    return {
      '_id': gameAnalysis.id,
      'gameId': gameAnalysis.gameId,
      'userId': gameAnalysis.userId,
      'analysedMoves': [AnalysedMoveBSONHandler.writes(am) for am in gameAnalysis.analysedMoves],
      'assessedMoves': [AssessedMoveBSONHandler.writes(am) for am in gameAnalysis.assessedMoves],
      'assessedChunks': [AssessedChunkBSONHandler.writes(am) for am in gameAnalysis.assessedChunks]
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
          ga.get('analysedMoves', []),
          ga.get('assessedMoves', []),
          ga.get('assessedChunks', [])))
    return gameAnalyses

  def byUserIds(self, userIds):
    return [self.byUserId(userId) for userId in userIds]

  def lazyWriteGames(self, gameAnalyses):
    [self.write(ga) for ga in gameAnalyses.gameAnalyses]