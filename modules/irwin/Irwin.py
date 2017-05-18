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
from modules.irwin.PVDrawAssessment import PVDrawAssessment
from modules.irwin.PVLosingAssessment import PVLosingAssessment
from modules.irwin.PVOverallAssessment import PVOverallAssessment
from modules.irwin.OverallAssessment import OverallAssessment
from modules.irwin.TrainingStats import TrainingStats, Accuracy, Sample
from modules.irwin.FalseReports import FalseReport, FalseReports
from modules.core.PlayerAnalysis import PlayerAnalysis
from modules.core.GameAnalyses import GameAnalyses


class Irwin(namedtuple('Irwin', ['api', 'learner', 'trainingStatsDB', 'playerAnalysisDB', 'falseReportsDB', 'settings'])):
  def train(self, forcetrain, updateAll, testOnly, fastTest): # runs forever
    if self.learner or testOnly or fastTest:
      TrainAndEvaluate(self.api, self.trainingStatsDB, self.playerAnalysisDB, self.falseReportsDB, self.settings, forcetrain, updateAll, testOnly, fastTest).start()

  @staticmethod
  def assessGame(gameAnalysis):
    gameAnalysis.assessedMoves = MoveAssessment.applyNet(gameAnalysis.tensorInputMoves())
    gameAnalysis.assessedChunks = ChunkAssessment.applyNet(gameAnalysis.tensorInputChunks())
    gameAnalysis.assessed = True
    return gameAnalysis

  @staticmethod
  def assessPlayer(playerAnalysis):
    playerAnalysis1 = PlayerAnalysis(
      id = playerAnalysis.id,
      titled = playerAnalysis.titled,
      engine = playerAnalysis.engine,
      gamesPlayed = playerAnalysis.gamesPlayed,
      closedReports = playerAnalysis.closedReports,
      gameAnalyses = GameAnalyses([Irwin.assessGame(gameAnalysis) for gameAnalysis in playerAnalysis.gameAnalyses.gameAnalyses]),
      PVAssessment = None,
      PVDrawAssessment = None,
      PVLosingAssessment = None,
      PVOverallAssessment = None,
      overallAssessment = None
    )
    irwinReportPV = PVAssessment.applyNet([playerAnalysis1.tensorInputPVs()])[0]
    irwinReportPVDraw = PVDrawAssessment.applyNet([playerAnalysis1.tensorInputPVs()])[0]
    irwinReportPVLosing = PVLosingAssessment.applyNet([playerAnalysis1.tensorInputPVs()])[0]
    irwinReportPVOverall = PVOverallAssessment.applyNet([[irwinReportPV.activation, irwinReportPVDraw.activation, irwinReportPVLosing.activation]])[0]
    
    playerAnalysis2 = PlayerAnalysis(
      id = playerAnalysis1.id,
      titled = playerAnalysis1.titled,
      engine = playerAnalysis1.engine,
      gamesPlayed = playerAnalysis1.gamesPlayed,
      closedReports = playerAnalysis1.closedReports,
      gameAnalyses = playerAnalysis1.gameAnalyses,
      PVAssessment = irwinReportPV.activation,
      PVDrawAssessment = irwinReportPVLosing.activation,
      PVLosingAssessment = irwinReportPVDraw.activation,
      PVOverallAssessment = irwinReportPVOverall.activation,
      overallAssessment = playerAnalysis1.overallAssessment
    )

    irwinReportOverallAssessment = OverallAssessment.applyNet([playerAnalysis2.tensorInputOverallAssessment()])[0]

    return PlayerAnalysis(
      id = playerAnalysis1.id,
      titled = playerAnalysis1.titled,
      engine = playerAnalysis1.engine,
      gamesPlayed = playerAnalysis1.gamesPlayed,
      closedReports = playerAnalysis1.closedReports,
      gameAnalyses = playerAnalysis1.gameAnalyses,
      PVAssessment = irwinReportPV.activation,
      PVDrawAssessment = irwinReportPVLosing.activation,
      PVLosingAssessment = irwinReportPVDraw.activation,
      PVOverallAssessment = irwinReportPVOverall.activation,
      overallAssessment = irwinReportOverallAssessment.activation
    )

  @staticmethod
  def flatten(listOfLists):
    return [val for sublist in listOfLists for val in sublist]

  @staticmethod
  def assessPlayers(playerAnalyses): # fast and ugly mode
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
        PVAssessment = playerAnalysis.PVAssessment,
        PVDrawAssessment = playerAnalysis.PVDrawAssessment,
        PVLosingAssessment = playerAnalysis.PVLosingAssessment,
        PVOverallAssessment = playerAnalysis.PVOverallAssessment,
        overallAssessment = playerAnalysis.overallAssessment
      ))
    pvTensors = [p.tensorInputPVs() for p in playerAnalyses1]
    pvDrawTensors = [p.tensorInputPVsDraw() for p in playerAnalyses1]
    pvLosingTensors = [p.tensorInputPVsLosing() for p in playerAnalyses1]

    assessedPVs = PVAssessment.applyNet(pvTensors)
    assessedDrawPVs = PVDrawAssessment.applyNet(pvDrawTensors)
    assessedLosingPVs = PVLosingAssessment.applyNet(pvLosingTensors)

    pvOverallTensors = [[pv.activation, pvDraw.activation, pvLosing.activation] for pv, pvDraw, pvLosing in zip(assessedPVs, assessedDrawPVs, assessedLosingPVs)]

    assessedOverallPVs = PVOverallAssessment.applyNet(pvOverallTensors)

    playerAnalyses2 = []
    for playerAnalysis, playerAnalysis1, irwinReportPV, irwinReportPVDraw, irwinReportPVLosing, irwinReportPVOverall in zip(playerAnalyses, playerAnalyses1, assessedPVs, assessedDrawPVs, assessedLosingPVs, assessedOverallPVs):
      playerAnalyses2.append(PlayerAnalysis(
        id = playerAnalysis.id,
        titled = playerAnalysis.titled,
        engine = playerAnalysis.engine,
        gamesPlayed = playerAnalysis.gamesPlayed,
        closedReports = playerAnalysis.closedReports,
        gameAnalyses = playerAnalysis1.gameAnalyses,
        PVAssessment = irwinReportPV.activation,
        PVDrawAssessment = irwinReportPVDraw.activation,
        PVLosingAssessment = irwinReportPVLosing.activation,
        PVOverallAssessment = irwinReportPVOverall.activation,
        overallAssessment = playerAnalysis1.overallAssessment
      ))

    overallAssessmentTensors = [p.tensorInputOverallAssessment() for p in playerAnalyses2]
    assessedOverallAssessments = OverallAssessment.applyNet(overallAssessmentTensors)

    outputPlayerAnalyses = []
    for playerAnalysis, irwinReportOverallAssessment in zip(playerAnalyses2, assessedOverallAssessments):
      outputPlayerAnalyses.append(PlayerAnalysis(
        id = playerAnalysis.id,
        titled = playerAnalysis.titled,
        engine = playerAnalysis.engine,
        gamesPlayed = playerAnalysis.gamesPlayed,
        closedReports = playerAnalysis.closedReports,
        gameAnalyses = playerAnalysis.gameAnalyses,
        PVAssessment = playerAnalysis.PVAssessment,
        PVDrawAssessment = playerAnalysis.PVDrawAssessment,
        PVLosingAssessment = playerAnalysis.PVLosingAssessment,
        PVOverallAssessment = playerAnalysis.PVOverallAssessment,
        overallAssessment = irwinReportOverallAssessment.activation
      ))
    return outputPlayerAnalyses

class TrainAndEvaluate(threading.Thread):
  def __init__(self, api, trainingStatsDB, playerAnalysisDB, falseReportsDB, settings, forcetrain, updateAll, testOnly, fastTest):
    threading.Thread.__init__(self)
    self.api = api
    self.trainingStatsDB = trainingStatsDB
    self.playerAnalysisDB = playerAnalysisDB
    self.falseReportsDB = falseReportsDB
    self.settings = settings
    self.forcetrain = forcetrain
    self.updateAll = updateAll
    self.testOnly = testOnly
    self.fastTest = fastTest

  def run(self):
    while True:
      time.sleep(10)
      if self.outOfDate() or self.forcetrain or self.testOnly or self.fastTest:
        logging.warning("OUT OF DATE: UPDATING!")
        trainer = TrainNetworks(self.api, self.playerAnalysisDB, self.settings['training']['minStep'], self.settings['training']['incStep'], self.updateAll, self.testOnly)
        trainer.start()
        trainer.join()
        engines = self.playerAnalysisDB.engines()
        legits = self.playerAnalysisDB.legits()
        unsorted = self.playerAnalysisDB.countUnsorted()
        logging.warning("Assessing new networks")
        if not self.fastTest:
          engines = Irwin.assessPlayers(engines)
          legits = Irwin.assessPlayers(legits)

        falseReports = FalseReports(
          falsePositives = [FalseReport(fp.id, fp.overallAssessment) for fp in legits if fp.isLegit(self.settings['thresholds']) == False],
          falseNegatives = [FalseReport(fn.id, fn.overallAssessment) for fn in engines if fn.isLegit(self.settings['thresholds']) == True])

        logging.warning("Calculating results")
        truePositive = sum([int(False == p.isLegit(self.settings['thresholds'])) for p in engines]) # cheaters marked as cheaters
        trueNegative = sum([int(True == p.isLegit(self.settings['thresholds'])) for p in legits]) # legits not marked or left open
        falsePositive = len(falseReports.falsePositives) # legits marked as engines
        falseNegative = len(falseReports.falseNegatives) # cheaters marked as legits
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
        self.falseReportsDB.write(falseReports)
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