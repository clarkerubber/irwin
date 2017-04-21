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

from modules.irwin.IrwinReport import IrwinReportBSONHandler

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
    self.assessedMoves = assessedMoves # List[IrwinReport] (Assessed by Irwin/TensorFlow)
    self.assessedChunks = assessedChunks # List[IrwinReport] (groups of 10 moves assessed by Irwin/TensorFlow)
    
    self.analysed = len(self.analysedMoves) > 0
    self.assessed = len(self.assessedMoves) > 0

    self.playableGame = chess.pgn.read_game(StringIO(game.pgn))
    self.white = self.playerAssessment.white

  def __str__(self):
    return 'GameAnalysis('+self.id+', '+str(self.assessedMoves)+', '+str(self.assessedChunks)+')'

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
    if len(assessedChunks) > 0:
      return numpy.mean([chunk.activation for chunk in assessedChunks])
    return 0

  def normalisedAssessedMoves(self):
    if self.assessed: # bear with me here. Average of the move (60%) and all the chunks that cover it (40%).
      return [(
        0.6 * assessedMove.activation + 
        0.4 * GameAnalysis.averageChunks(self.assessedChunks[max(0,move-10):min(len(self.assessedChunks),move+1)])
      ) for move, assessedMove in enumerate(self.assessedMoves)]
    return []

  def assessmentOutlierAverage(self):
    if self.assessed:
      norm = sorted(self.normalisedAssessedMoves())
      top20Percent = norm[-int(0.2*len(norm)):]
      if len(top20Percent) > 0:
        mean = numpy.mean(top20Percent)
      else:
        mean = 0
      if not numpy.isnan(mean):
        return int(mean)
    return 0

  def assessmentAverage(self):
    if self.assessed:
      norm = self.normalisedAssessedMoves()
      if len(norm) > 0:
        mean = numpy.mean(norm)
      else:
        mean = 0
      if not numpy.isnan(mean):
        return int(mean)
    return 0


def gameAnalysisId(gameId, white):
  return gameId + '/' + ('white' if white else 'black')

class GameAnalysisBSONHandler:
  @staticmethod
  def reads(game, playerAssessment, analysedMovesBSON, assessedMovesBSON, assessedChunksBSON):
    return GameAnalysis(
      game,
      playerAssessment,
      [AnalysedMoveBSONHandler.reads(am) for am in analysedMovesBSON],
      [IrwinReportBSONHandler.reads(am) for am in assessedMovesBSON],
      [IrwinReportBSONHandler.reads(ac) for ac in assessedChunksBSON])

  @staticmethod
  def writes(gameAnalysis):
    return {
      '_id': gameAnalysis.id,
      'gameId': gameAnalysis.gameId,
      'userId': gameAnalysis.userId,
      'analysedMoves': [AnalysedMoveBSONHandler.writes(am) for am in gameAnalysis.analysedMoves],
      'assessedMoves': [IrwinReportBSONHandler.writes(am) for am in gameAnalysis.assessedMoves],
      'assessedChunks': [IrwinReportBSONHandler.writes(am) for am in gameAnalysis.assessedChunks]
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