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
  def __init__(self, game, playerAssessment, analysedMoves, assessedMoves, assessedChunks, moveChunkActivation):
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

    self.moveChunkActivation = moveChunkActivation
    
    self.analysed = len(self.analysedMoves) > 0
    self.assessed = len(self.assessedMoves) > 0 and len(self.assessedChunks) > 0

    self.playableGame = chess.pgn.read_game(StringIO(game.pgn))
    self.white = self.playerAssessment.white

  def __str__(self):
    return 'GameAnalysis({}, analysedMoves: {}, assessedMoves: {}, assessedChunks: {}, moveChunkActivation: {})'.format(
      self.id, len(self.analysedMoves), len(self.assessedMoves), len(self.assessedChunks), self.moveChunkActivation)

  def activation(self):
    return min(self.moveChunkActivation, self.top3Average())

  def reportDict(self):
    return {
      'gameId': self.gameId,
      'activation': self.activation(),
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

  def moveActivations(self):
    return [move.activation for move in self.assessedMoves]

  def chunkActivations(self):
    return [chunk.activation for chunk in self.assessedChunks]

  def tensorInputChunks(self):
    allChunks = [[
        analysedMove.rank(),
        int(100*analysedMove.winningChancesLoss()),
        int(100*analysedMove.advantage()),
        analysedMove.ambiguity(),
        int(self.consistentMoveTime(analysedMove.move)),
        int(analysedMove.emt),
        int(100*(analysedMove.rank()+1)/analysedMove.ambiguity()),
        int(1 if analysedMove.onlyMove() else -1)
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
      int(analysedMove.emt),
      int(100*(analysedMove.rank()+1)/analysedMove.ambiguity()),
      int(1 if analysedMove.onlyMove() else -1)] for analysedMove in self.analysedMoves]

  def tensorInputMoveChunks(self):
    return self.binnedMoveActivations() + self.binnedChunkActivations() + self.proportionalBinnedMoveActivations() + self.proportionalBinnedChunkActivations() + self.streaksBinned() + [self.winningIndex()] # list of 20 ints

  def winningIndex(self): # move number where the player has > 50% winning chances
    try:
      return [m.winning() for m in self.analysedMoves].index(True)
    except ValueError:
      return 0

  def maxStreak(self, threshold):
    hotNams = [nam > threshold for nam in self.normalisedAssessedMoves()]
    maxCount = 0
    count = 0
    for i in hotNams:
      if i:
        count += 1
        if count > maxCount:
          maxCount = count
      else:
        count = 0
    return maxCount

  def streaksBinned(self):
    brackets = [60, 70, 80]
    bins = [0, 0, 0]
    for i, b in enumerate(brackets):
      bins[i] = self.maxStreak(b)
    return bins

  def top3Average(self):
    top3 = sorted(self.normalisedAssessedMoves())[-3:]
    if len(top3) > 0:
      return int(numpy.mean(top3))
    return 0

  @staticmethod
  def averageChunks(assessedChunks):
    if len(assessedChunks) > 0:
      return numpy.mean([chunk.activation for chunk in assessedChunks])
    return 0

  def binnedMoveActivations(self):
    bins = [0, 0, 0, 0] # 4 bins representing 90-100%, 80-100%, 50-100%, 0-50%
    brackets = [(90, 100), (80, 100), (50, 100), (0, 49)]
    activations = [assessedMove.activation for assessedMove in self.assessedMoves]
    for i, b in enumerate(brackets):
      bins[i] = sum([a >= b[0] and a <= b[1] for a in activations])
    return bins

  def proportionalBinnedMoveActivations(self):
    bins = [0, 0, 0, 0]
    bgActivations = self.binnedMoveActivations()
    s = len(self.assessedMoves)
    if s > 0:
      for i, b in enumerate(bgActivations):
        bins[i] = int(100*b/s)
    return bins

  def binnedChunkActivations(self):
    bins = [0, 0, 0, 0] # 4 bins representing 90-100%, 80-100%, 50-100%, 0-50%
    brackets = [(90, 100), (80, 100), (50, 100), (0, 49)]
    activations = [assessedChunk.activation for assessedChunk in self.assessedChunks]
    for i, b in enumerate(brackets):
      bins[i] = sum([a >= b[0] and a <= b[1] for a in activations])
    return bins

  def proportionalBinnedChunkActivations(self):
    bins = [0, 0, 0, 0]
    bgActivations = self.binnedChunkActivations()
    s = len(self.assessedChunks)
    if s > 0:
      for i, b in enumerate(bgActivations):
        bins[i] = int(100*b/s)
    return bins

  def normalisedAssessedMoves(self):
    if self.assessed: # bear with me here. Average of the move (50%) and all the chunks that cover it (50%).
      return [(
        0.50 * assessedMove.activation + 
        0.50 * GameAnalysis.averageChunks(self.assessedChunks[max(0,move-10):min(len(self.assessedChunks),move+1)])
      ) for move, assessedMove in enumerate(self.assessedMoves)]
    return []

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
  def reads(game, playerAssessment, analysedMovesBSON, assessedMovesBSON, assessedChunksBSON, moveChunkActivation):
    return GameAnalysis(
      game = game,
      playerAssessment = playerAssessment,
      analysedMoves = [AnalysedMoveBSONHandler.reads(am) for am in analysedMovesBSON],
      assessedMoves = [IrwinReportBSONHandler.reads(am) for am in assessedMovesBSON],
      assessedChunks = [IrwinReportBSONHandler.reads(ac) for ac in assessedChunksBSON],
      moveChunkActivation = moveChunkActivation)

  @staticmethod
  def writes(gameAnalysis):
    return {
      '_id': gameAnalysis.id,
      'gameId': gameAnalysis.gameId,
      'userId': gameAnalysis.userId,
      'analysedMoves': [AnalysedMoveBSONHandler.writes(am) for am in gameAnalysis.analysedMoves],
      'assessedMoves': [IrwinReportBSONHandler.writes(am) for am in gameAnalysis.assessedMoves],
      'assessedChunks': [IrwinReportBSONHandler.writes(am) for am in gameAnalysis.assessedChunks],
      'moveChunkActivation': gameAnalysis.moveChunkActivation
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
          ga.get('assessedChunks', []),
          ga.get('moveChunkActivation', None)))
    return gameAnalyses

  def byUserIds(self, userIds):
    return [self.byUserId(userId) for userId in userIds]

  def lazyWriteGames(self, gameAnalyses):
    [self.write(ga) for ga in gameAnalyses.gameAnalyses]
