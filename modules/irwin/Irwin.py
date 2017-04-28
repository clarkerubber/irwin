from collections import namedtuple
import threading
import datetime
import time
import logging
import itertools

from modules.irwin.TrainNetworks import TrainNetworks
from modules.irwin.MoveAssessment import MoveAssessment
from modules.irwin.ChunkAssessment import ChunkAssessment
from modules.irwin.TrainingStats import TrainingStats, Accuracy, Sample
from modules.core.PlayerAnalysis import PlayerAnalysis
from modules.core.GameAnalyses import GameAnalyses


class Irwin(namedtuple('Irwin', ['api', 'learner', 'trainingStatsDB', 'playerAnalysisDB'])):
  def train(self): # runs forever
    if self.learner == 1:
      TrainAndEvaluate(self.api, self.trainingStatsDB, self.playerAnalysisDB).start()

  @staticmethod
  def assessGame(gameAnalysis, titled):
    gameAnalysis.assessedMoves = MoveAssessment.applyNet(gameAnalysis.tensorInputMoves(titled))
    gameAnalysis.assessedChunks = ChunkAssessment.applyNet(gameAnalysis.tensorInputChunks(titled))
    gameAnalysis.assessed = True
    return gameAnalysis

  @staticmethod
  def assessPlayer(playerAnalysis):
    return PlayerAnalysis(
      id = playerAnalysis.id,
      titled = playerAnalysis.titled,
      engine = playerAnalysis.engine,
      gamesPlayed = playerAnalysis.gamesPlayed,
      closedReports = playerAnalysis.closedReports,
      gameAnalyses = GameAnalyses([Irwin.assessGame(gameAnalysis, playerAnalysis.titled) for gameAnalysis in playerAnalysis.gameAnalyses.gameAnalyses])
    )

  @staticmethod
  def flatten(listOfLists):
    return [val for sublist in listOfLists for val in sublist]

  @staticmethod
  def assessPlayers(playerAnalyses): # fast mode
    moves = []
    chunks = []
    for playerAnalysis in playerAnalyses:
      moves.extend(Irwin.flatten([gameAnalysis.tensorInputMoves(playerAnalysis.titled) for gameAnalysis in playerAnalysis.gameAnalyses.gameAnalyses]))
      chunks.extend(Irwin.flatten([gameAnalysis.tensorInputChunks(playerAnalysis.titled) for gameAnalysis in playerAnalysis.gameAnalyses.gameAnalyses]))

    assessedMoves = MoveAssessment.applyNet(moves)
    assessedChunks = ChunkAssessment.applyNet(chunks)
    moveHeader = 0
    chunkHeader = 0
    outputPlayerAnalyses = []

    for playerAnalysis in playerAnalyses:
      outputGameAnalyses = GameAnalyses([])
      for gameAnalysis in playerAnalysis.gameAnalyses.gameAnalyses:
        lenM = len(gameAnalysis.tensorInputMoves(playerAnalysis.titled))
        lenC = len(gameAnalysis.tensorInputChunks(playerAnalysis.titled))
        gameAnalysis.assessedMoves = assessedMoves[moveHeader:moveHeader+lenM]
        gameAnalysis.assessedChunks = assessedChunks[chunkHeader:chunkHeader+lenC]
        gameAnalysis.assessed = True
        moveHeader = moveHeader+lenM
        chunkHeader = chunkHeader+lenC
        outputGameAnalyses.append(gameAnalysis)

      outputPlayerAnalyses.append(PlayerAnalysis(
        id = playerAnalysis.id,
        titled = playerAnalysis.titled,
        engine = playerAnalysis.engine,
        gamesPlayed = playerAnalysis.gamesPlayed,
        closedReports = playerAnalysis.closedReports,
        gameAnalyses = outputGameAnalyses
      ))
    return outputPlayerAnalyses

class TrainAndEvaluate(threading.Thread):
  def __init__(self, api, trainingStatsDB, playerAnalysisDB):
    threading.Thread.__init__(self)
    self.api = api
    self.trainingStatsDB = trainingStatsDB
    self.playerAnalysisDB = playerAnalysisDB

  def run(self):
    while True:
      time.sleep(10)
      if self.outOfDate():
        logging.warning("OUT OF DATE: UPDATING!")
        trainer = TrainNetworks(self.api, self.playerAnalysisDB)
        trainer.start()
        engines = self.playerAnalysisDB.engines()
        legits = self.playerAnalysisDB.legits()
        trainer.join()
        unsorted = self.playerAnalysisDB.countUnsorted()
        logging.warning("Assessing new networks")
        engines = Irwin.assessPlayers(engines)
        legits = Irwin.assessPlayers(legits)

        logging.warning("Calculating results")
        truePositive = sum([int(False == p.isLegit()) for p in engines]) # cheaters marked as cheaters
        trueNegative = sum([int(True == p.isLegit()) for p in legits]) # legits not marked or left open
        falsePositive = sum([int(False == p.isLegit()) for p in legits]) # legits marked as engines
        falseNegative = sum([int(True == p.isLegit()) for p in engines]) # cheaters marked as legits
        indeciseEngines = sum([int(p.isLegit() is None) for p in engines])
        indeciseLegits = sum([int(p.isLegit() is None) for p in legits])

        logging.warning("Writing training stats")
        self.trainingStatsDB.write(TrainingStats(
          date = datetime.datetime.utcnow(),
          sample = Sample(engines = len(engines), legits = len(legits), unprocessed = unsorted),
          accuracy = Accuracy(
            truePositive = truePositive,
            trueNegative = trueNegative,
            falsePositive = falsePositive,
            falseNegative = falseNegative,
            indeciseEngines = indeciseEngines,
            indeciseLegits = indeciseLegits)))

  def outOfDate(self):
    latest = self.trainingStatsDB.latest()
    if latest is not None:
      if datetime.datetime.utcnow() - latest.date > datetime.timedelta(days=1): # if it has been over a day since the last training
        return True
    else:
      return True
    return False