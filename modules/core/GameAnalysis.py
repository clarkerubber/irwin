import chess
import chess.pgn
import logging
import numpy
import itertools

from modules.bcolors.bcolors import bcolors

from modules.core.PlayerAssessment import PlayerAssessment
from modules.core.AnalysedMove import AnalysedMove, Analysis, Score
from modules.core.Game import GameBSONHandler
from modules.core.GameAnalyses import GameAnalyses
from modules.core.AnalysedMove import AnalysedMoveBSONHandler, winningChances

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
    return 'GameAnalysis({}, analysedMoves: {}, assessedMoves: {}, assessedChunks: {})'.format(
      self.id, len(self.analysedMoves), len(self.assessedMoves), len(self.assessedChunks))

  def reportDict(self):
    return {
      'gameId': self.gameId,
      'activation': self.assessmentAverage(),
      'moves': self.movesReportDict()
    }

  def movesReportDict(self):
    if self.analysed:
      return [{
        'activation': int(nam),
        'rank': am.trueRank(),
        'ambiguity': am.ambiguity(),
        'odds': int(100*am.advantage()),
        'loss': int(100*am.winningChancesLoss())
      } for nam, am in zip(self.normalisedAssessedMoves(), self.analysedMoves)]
    return []

  def rankedMoves(self): # Moves where the played move is in top 5
    return [am for am in self.analysedMoves if am.inAnalyses()]

  def ply(self, moveNumber):
    return (2*(moveNumber-1)) + (0 if self.white else 1)

  def consistentMoveTime(self, moveNumber):
    emt = self.game.emts[self.ply(moveNumber)]
    return not self.game.isEmtOutlier(emt)

  def tensorInputChunks(self):
    allChunks = [[
        analysedMove.rank(),
        int(100*analysedMove.winningChancesLoss()),
        int(100*analysedMove.advantage()),
        analysedMove.ambiguity(),
        int(self.consistentMoveTime(analysedMove.move)),
        int(analysedMove.emt)
    ] for analysedMove in self.analysedMoves]

    entries = []
    for i in range(len(self.analysedMoves) - 9):
      entry = [i]
      entry.extend(itertools.chain(*allChunks[i:i+10]))
      entries.append(entry)
    return entries

  def tensorInputMoves(self):
    return [[
      analysedMove.move,
      analysedMove.rank(),
      int(100*analysedMove.winningChancesLoss()),
      int(100*analysedMove.advantage()),
      analysedMove.ambiguity(),
      int(self.consistentMoveTime(analysedMove.move)),
      int(analysedMove.emt)] for analysedMove in self.analysedMoves]

  @staticmethod
  def averageChunks(assessedChunks):
    if len(assessedChunks) > 0:
      return numpy.mean([chunk.activation for chunk in assessedChunks])
    return 0

  def normalisedAssessedMoves(self):
    if self.assessed: # bear with me here. Average of the move (40%) and all the chunks that cover it (60%).
      return [(
        0.40 * assessedMove.activation + 
        0.60 * GameAnalysis.averageChunks(self.assessedChunks[max(0,move-10):min(len(self.assessedChunks),move+1)])
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

  def assessmentNoOutlierAverage(self):
    if self.assessed:
      norm = sorted(self.normalisedAssessedMoves())
      top80Percent = norm[-int(0.8*len(norm)):]
      if len(top80Percent) > 0:
        mean = numpy.mean(top80Percent)
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

  def pv0ByAmbiguity(self, ambiguity):
    return sum(int(analysedMove.trueRank() == 1) for analysedMove in self.analysedMoves if analysedMove.ambiguity() == ambiguity)

  def ambiguitySum(self, ambiguity): # Amount of positions where ambiguity == X
    return sum(int(analysedMove.ambiguity() == ambiguity) for analysedMove in self.analysedMoves)

  def pv0ByAmbiguityStats(self): # [{sum of pv0 moves given X ambiguity, amount of positions with X ambiguity}]
    return [(self.pv0ByAmbiguity(ambiguity), self.ambiguitySum(ambiguity)) for ambiguity in range (1, 6)]

def gameAnalysisId(gameId, white):
  return gameId + '/' + ('white' if white else 'black')

class GameAnalysisBSONHandler:
  @staticmethod
  def reads(game, playerAssessment, analysedMovesBSON, assessedMovesBSON, assessedChunksBSON):
    return GameAnalysis(
      game = game,
      playerAssessment = playerAssessment,
      analysedMoves = [AnalysedMoveBSONHandler.reads(am) for am in analysedMovesBSON],
      assessedMoves = [IrwinReportBSONHandler.reads(am) for am in assessedMovesBSON],
      assessedChunks = [IrwinReportBSONHandler.reads(ac) for ac in assessedChunksBSON])

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
