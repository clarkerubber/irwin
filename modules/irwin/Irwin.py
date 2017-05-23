from collections import namedtuple
import threading
import datetime
import time
import logging
import itertools

from modules.irwin.TrainNetworks import TrainNetworks

from modules.irwin.MoveAssessment import MoveAssessment
from modules.irwin.ChunkAssessment import ChunkAssessment
from modules.irwin.MoveChunkAssessment import MoveChunkAssessment
from modules.irwin.GamePVAssessment import GamePVAssessment
from modules.irwin.PlayerPVAssessment import PlayerPVAssessment
from modules.irwin.GamesAssessment import GamesAssessment

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
    gameAnalysis.pvActivation = GamePVAssessment.applyNet([gameAnalysis.tensorInputGamePVs()])[0].activation
    gameAnalysis.moveChunkActivation = MoveChunkAssessment.applyNet([gameAnalysis.tensorInputMoveChunks()])[0].activation
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
      gamesActivation = None,
      pvActivation = None
    )

    return PlayerAnalysis(
      id = playerAnalysis1.id,
      titled = playerAnalysis1.titled,
      engine = playerAnalysis1.engine,
      gamesPlayed = playerAnalysis1.gamesPlayed,
      closedReports = playerAnalysis1.closedReports,
      gameAnalyses = playerAnalysis1.gameAnalyses,
      gamesActivation = GamesAssessment.applyNet([playerAnalysis1.tensorInputGames()])[0].activation,
      pvActivation = PlayerPVAssessment.applyNet([playerAnalysis1.tensorInputPlayerPVs()])[0].activation
    )

  @staticmethod
  def flatten(listOfLists):
    return [val for sublist in listOfLists for val in sublist]

  @staticmethod
  def assessPlayers(playerAnalyses): # fast and ugly mode
    moves = []
    chunks = []
    pvs = []
    for playerAnalysis in playerAnalyses:
      moves.extend(Irwin.flatten([gameAnalysis.tensorInputMoves() for gameAnalysis in playerAnalysis.gameAnalyses.gameAnalyses]))
      chunks.extend(Irwin.flatten([gameAnalysis.tensorInputChunks() for gameAnalysis in playerAnalysis.gameAnalyses.gameAnalyses]))
      pvs.extend([gameAnalysis.tensorInputGamePVs() for gameAnalysis in playerAnalysis.gameAnalyses.gameAnalyses])

    assessedMoves = MoveAssessment.applyNet(moves)
    assessedChunks = ChunkAssessment.applyNet(chunks)
    assessedPVs = GamePVAssessment.applyNet(pvs)
    moveHeader = 0
    chunkHeader = 0
    pvHeader = 0
    playerAnalyses1 = []

    gameAnalyses1 = GameAnalyses([])
    for playerAnalysis in playerAnalyses:
      for gameAnalysis in playerAnalysis.gameAnalyses.gameAnalyses:
        lenM = len(gameAnalysis.tensorInputMoves())
        lenC = len(gameAnalysis.tensorInputChunks())
        gameAnalysis.assessedMoves = assessedMoves[moveHeader:moveHeader+lenM]
        gameAnalysis.assessedChunks = assessedChunks[chunkHeader:chunkHeader+lenC]
        gameAnalysis.pvActivation = assessedPVs[pvHeader].activation
        moveHeader += lenM
        chunkHeader += lenC
        pvHeader += 1
        gameAnalyses1.append(gameAnalysis)

    assessedMoveChunks = MoveChunkAssessment.applyNet([gameAnalysis.tensorInputMoveChunks() for gameAnalysis in gameAnalyses1.gameAnalyses])

    gameAnalyses2 = GameAnalyses([])
    for gameAnalysis, moveChunkIrwinReport in zip(gameAnalyses1.gameAnalyses, assessedMoveChunks):
      gameAnalysis.moveChunkActivation = moveChunkIrwinReport.activation
      gameAnalysis.assessed = True
      gameAnalyses2.append(gameAnalysis)

    playerAnalyses1 = []
    tensorInputGames = []
    tensorInputPlayerPVs = []
    gameHeader = 0
    for playerAnalysis in playerAnalyses:
      lenG = len(playerAnalysis.gameAnalyses.gameAnalyses)
      pa = PlayerAnalysis(
        id = playerAnalysis.id,
        titled = playerAnalysis.titled, 
        engine = playerAnalysis.engine, 
        gamesPlayed = playerAnalysis.gamesPlayed,
        closedReports = playerAnalysis.closedReports,
        gameAnalyses = GameAnalyses(gameAnalyses2.gameAnalyses[gameHeader:gameHeader+lenG]),
        gamesActivation = None,
        pvActivation = None
      )
      playerAnalyses1.append(pa)
      tensorInputGames.append(pa.tensorInputGames())
      tensorInputPlayerPVs.append(pa.tensorInputPlayerPVs())
      gameHeader += lenG

    playerAnalyses2 = []
    gameIrwinReports = GamesAssessment.applyNet(tensorInputGames)
    playerPVIrwinReports = PlayerPVAssessment.applyNet(tensorInputPlayerPVs)
    for playerAnalysis, gameIrwinReport, playerPVIrwinReport in zip(playerAnalyses1, gameIrwinReports, playerPVIrwinReports):
      playerAnalyses2.append(PlayerAnalysis(
        id = playerAnalysis.id,
        titled = playerAnalysis.titled, 
        engine = playerAnalysis.engine, 
        gamesPlayed = playerAnalysis.gamesPlayed,
        closedReports = playerAnalysis.closedReports,
        gameAnalyses = playerAnalysis.gameAnalyses,
        gamesActivation = gameIrwinReport.activation,
        pvActivation = playerPVIrwinReport.activation))

    return playerAnalyses2

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
        unsorted = self.playerAnalysisDB.countUnsorted()

        # Counters for engines
        truePositives = 0
        indeciseEngines = 0
        falseNegatives = []

        page = 0
        engines = self.playerAnalysisDB.enginesPaginated(page)
        while len(engines) > 0:
          logging.warning("Engines page: " + str(page))
          if not self.fastTest:
            engines = Irwin.assessPlayers(engines)
            self.playerAnalysisDB.lazyWriteMany(engines)
          truePositives += len([1 for p in engines if p.isLegit(self.settings['thresholds']) == False])
          indeciseEngines += len([1 for p in engines if p.isLegit(self.settings['thresholds']) is None])
          falseNegatives.extend([FalseReport(fn.id, fn.activation()) for fn in engines if fn.isLegit(self.settings['thresholds']) == True])

          page += 1
          engines = self.playerAnalysisDB.enginesPaginated(page)

        # Counters for legits
        trueNegatives = 0
        indeciseLegits = 0
        falsePositives = []

        page = 0
        legits = self.playerAnalysisDB.legitsPaginated(page)
        while len(legits) > 0:
          logging.warning("Legits page: " + str(page))
          if not self.fastTest:
            legits = Irwin.assessPlayers(legits)
            self.playerAnalysisDB.lazyWriteMany(legits)
          trueNegatives += len([1 for p in legits if p.isLegit(self.settings['thresholds']) == True])
          indeciseLegits += len([1 for p in legits if p.isLegit(self.settings['thresholds']) is None])
          falsePositives.extend([FalseReport(fp.id, fp.activation()) for fp in legits if fp.isLegit(self.settings['thresholds']) == False])

          page += 1
          legits = self.playerAnalysisDB.legitsPaginated(page)

        logging.warning("Writing training stats")
        self.trainingStatsDB.write(TrainingStats(
          date = datetime.datetime.utcnow(),
          sample = Sample(engines = truePositives + indeciseEngines + len(falseNegatives), legits = trueNegatives + indeciseLegits + len(falsePositives), unprocessed = unsorted),
          accuracy = Accuracy(
            truePositive = truePositives,
            trueNegative = trueNegatives,
            falsePositive = len(falsePositives),
            falseNegative = len(falseNegatives),
            indeciseEngines = indeciseEngines,
            indeciseLegits = indeciseLegits)))
        self.falseReportsDB.write(FalseReports(falsePositives = falsePositives, falseNegatives = falseNegatives))

  def outOfDate(self):
    latest = self.trainingStatsDB.latest()
    if latest is not None:
      if datetime.datetime.utcnow() - latest.date > datetime.timedelta(days=1): # if it has been over a day since the last training
        return True
    else:
      return True
    return False