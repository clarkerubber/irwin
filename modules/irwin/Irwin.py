from collections import namedtuple
import threading
import datetime
import time
import logging
import itertools

from modules.irwin.TrainNetworks import TrainNetworks
from modules.irwin.MoveAssessment import MoveAssessment
from modules.irwin.ChunkAssessment import ChunkAssessment
from modules.irwin.PVAssessment import PVAssessment
from modules.irwin.TrainingStats import TrainingStats, Accuracy, Sample
from modules.irwin.FalsePositives import FalsePositive, FalsePositives
from modules.core.PlayerAnalysis import PlayerAnalysis
from modules.core.GameAnalyses import GameAnalyses


class Irwin(namedtuple('Irwin', ['api', 'learner', 'trainingStatsDB', 'playerAnalysisDB', 'falsePositivesDB', 'settings'])):
  def train(self, forcetrain, updateAll, testOnly): # runs forever
    if self.learner:
      TrainAndEvaluate(self.api, self.trainingStatsDB, self.playerAnalysisDB, self.falsePositivesDB, self.settings, forcetrain, updateAll, testOnly).start()

  @staticmethod
  def assessGame(gameAnalysis):
    gameAnalysis.assessedMoves = MoveAssessment.applyNet(gameAnalysis.tensorInputMoves())
    gameAnalysis.assessedChunks = ChunkAssessment.applyNet(gameAnalysis.tensorInputChunks())
    gameAnalysis.assessed = True
    return gameAnalysis

  @staticmethod
  def assessPlayer(playerAnalysis):
    outputPlayerAnalysis = PlayerAnalysis(
      id = playerAnalysis.id,
      titled = playerAnalysis.titled,
      engine = playerAnalysis.engine,
      gamesPlayed = playerAnalysis.gamesPlayed,
      closedReports = playerAnalysis.closedReports,
      gameAnalyses = GameAnalyses([Irwin.assessGame(gameAnalysis) for gameAnalysis in playerAnalysis.gameAnalyses.gameAnalyses]),
      PVAssessment = None,
    )
    irwinReport = PVAssessment.applyNet([outputPlayerAnalysis.tensorInputPVs()])[0]
    return PlayerAnalysis(
      id = playerAnalysis.id,
      titled = playerAnalysis.titled,
      engine = playerAnalysis.engine,
      gamesPlayed = playerAnalysis.gamesPlayed,
      closedReports = playerAnalysis.closedReports,
      gameAnalyses = outputPlayerAnalysis.gameAnalyses,
      PVAssessment = irwinReport.activation
    )

  @staticmethod
  def flatten(listOfLists):
    return [val for sublist in listOfLists for val in sublist]

  @staticmethod
  def assessPlayers(playerAnalyses): # fast mode
    moves = []
    chunks = []
    for playerAnalysis in playerAnalyses:
      moves.extend(Irwin.flatten([gameAnalysis.tensorInputMoves() for gameAnalysis in playerAnalysis.gameAnalyses.gameAnalyses]))
      chunks.extend(Irwin.flatten([gameAnalysis.tensorInputChunks() for gameAnalysis in playerAnalysis.gameAnalyses.gameAnalyses]))

    assessedMoves = MoveAssessment.applyNet(moves)
    assessedChunks = ChunkAssessment.applyNet(chunks)
    moveHeader = 0
    chunkHeader = 0
    playerAnalyses1 = []

    for playerAnalysis in playerAnalyses:
      outputGameAnalyses = GameAnalyses([])
      for gameAnalysis in playerAnalysis.gameAnalyses.gameAnalyses:
        lenM = len(gameAnalysis.tensorInputMoves())
        lenC = len(gameAnalysis.tensorInputChunks())
        gameAnalysis.assessedMoves = assessedMoves[moveHeader:moveHeader+lenM]
        gameAnalysis.assessedChunks = assessedChunks[chunkHeader:chunkHeader+lenC]
        gameAnalysis.assessed = True
        moveHeader = moveHeader+lenM
        chunkHeader = chunkHeader+lenC
        outputGameAnalyses.append(gameAnalysis)

      playerAnalyses1.append(PlayerAnalysis(
        id = playerAnalysis.id,
        titled = playerAnalysis.titled,
        engine = playerAnalysis.engine,
        gamesPlayed = playerAnalysis.gamesPlayed,
        closedReports = playerAnalysis.closedReports,
        gameAnalyses = outputGameAnalyses,
        PVAssessment = playerAnalysis.PVAssessment
      ))
    pvTensors = [p.tensorInputPVs() for p in playerAnalyses1]
    assessedPVs = PVAssessment.applyNet(pvTensors)
    outputPlayerAnalyses = []
    for playerAnalysis, playerAnalysis1, irwinReport in zip(playerAnalyses, playerAnalyses1, assessedPVs):
      outputPlayerAnalyses.append(PlayerAnalysis(
        id = playerAnalysis.id,
        titled = playerAnalysis.titled,
        engine = playerAnalysis.engine,
        gamesPlayed = playerAnalysis.gamesPlayed,
        closedReports = playerAnalysis.closedReports,
        gameAnalyses = playerAnalysis1.gameAnalyses,
        PVAssessment = irwinReport.activation
      ))
    return outputPlayerAnalyses

class TrainAndEvaluate(threading.Thread):
  def __init__(self, api, trainingStatsDB, playerAnalysisDB, falsePositivesDB, settings, forcetrain, updateAll, testOnly):
    threading.Thread.__init__(self)
    self.api = api
    self.trainingStatsDB = trainingStatsDB
    self.playerAnalysisDB = playerAnalysisDB
    self.falsePositivesDB = falsePositivesDB
    self.settings = settings
    self.forcetrain = forcetrain
    self.updateAll = updateAll
    self.testOnly = testOnly

  def run(self):
    while True:
      time.sleep(10)
      if self.outOfDate() or self.forcetrain or self.testOnly:
        logging.warning("OUT OF DATE: UPDATING!")
        trainer = TrainNetworks(self.api, self.playerAnalysisDB, self.settings['training']['minStep'], self.settings['training']['incStep'], self.updateAll, self.testOnly)
        trainer.start()
        engines = self.playerAnalysisDB.engines()
        legits = self.playerAnalysisDB.legits()
        trainer.join()
        unsorted = self.playerAnalysisDB.countUnsorted()
        logging.warning("Assessing new networks")
        engines = Irwin.assessPlayers(engines)
        legits = Irwin.assessPlayers(legits)

        logging.warning("Calculating results")
        falsePositives = FalsePositives([FalsePositive(fp.id, fp.activation()) for fp in legits if fp.isLegit(self.settings['thresholds']) == False])

        truePositive = sum([int(False == p.isLegit(self.settings['thresholds'])) for p in engines]) # cheaters marked as cheaters
        trueNegative = sum([int(True == p.isLegit(self.settings['thresholds'])) for p in legits]) # legits not marked or left open
        falsePositive = len(falsePositives.falsePositives) # legits marked as engines
        falseNegative = sum([int(True == p.isLegit(self.settings['thresholds'])) for p in engines]) # cheaters marked as legits
        indeciseEngines = sum([int(p.isLegit(self.settings['thresholds']) is None) for p in engines])
        indeciseLegits = sum([int(p.isLegit(self.settings['thresholds']) is None) for p in legits])

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
        self.falsePositivesDB.write(falsePositives)
        logging.warning("Writing updated player assessments")
        self.playerAnalysisDB.lazyWriteMany(engines + legits)

  def outOfDate(self):
    latest = self.trainingStatsDB.latest()
    if latest is not None:
      if datetime.datetime.utcnow() - latest.date > datetime.timedelta(days=1): # if it has been over a day since the last training
        return True
    else:
      return True
    return False