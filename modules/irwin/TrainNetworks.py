import threading
import logging

from modules.irwin.updatePlayerEngineStatus import updatePlayerEngineStatus
from modules.irwin.writeCSV import writeClassifiedMovesCSV, writeClassifiedChunksCSV, writeClassifiedMoveChunksCSV, writeClassifiedGamePVsCSV, writeClassifiedPlayerPVsCSV, writeClassifiedGamesCSV
from modules.irwin.MoveAssessment import MoveAssessment
from modules.irwin.ChunkAssessment import ChunkAssessment
from modules.irwin.MoveChunkAssessment import MoveChunkAssessment
from modules.irwin.GamePVAssessment import GamePVAssessment
from modules.irwin.PlayerPVAssessment import PlayerPVAssessment
from modules.irwin.GamesAssessment import GamesAssessment

class TrainNetworks(threading.Thread):
  def __init__(self, api, playerAnalysisDB, minTrainingSteps, incTrainingSteps, updateAll, trainOnly):
    threading.Thread.__init__(self)
    self.api = api
    self.playerAnalysisDB = playerAnalysisDB
    self.minTrainingSteps = minTrainingSteps
    self.incTrainingSteps = incTrainingSteps
    self.updateAll = updateAll
    self.trainOnly = trainOnly

  def run(self):
    if self.trainOnly and self.updateAll:
      updatePlayerEngineStatus(self.api, self.playerAnalysisDB, self.updateAll)
    if not self.trainOnly:
      updatePlayerEngineStatus(self.api, self.playerAnalysisDB, self.updateAll)
      logging.warning("Importing users for CSV dumps")
      sortedUsers = self.playerAnalysisDB.balancedSorted()
      logging.warning("Dumping stats to CSV")
      self.classifyMoves(sortedUsers)
      self.classifyChunks(sortedUsers)
      self.classifyMoveChunks(sortedUsers)
      self.classifyGamePVs(sortedUsers)
      self.classifyPlayerPVs(sortedUsers)
      self.classifyGames(sortedUsers)
      MoveAssessment.learn(self.minTrainingSteps, self.incTrainingSteps)
      ChunkAssessment.learn(self.minTrainingSteps, self.incTrainingSteps)
      MoveChunkAssessment.learn(self.minTrainingSteps, self.incTrainingSteps)
      GamePVAssessment.learn(self.minTrainingSteps, self.incTrainingSteps)
      PlayerPVAssessment.learn(self.minTrainingSteps, self.incTrainingSteps)
      GamesAssessment.learn(self.minTrainingSteps, self.incTrainingSteps)

  def classifyMoves(self, playerAnalyses):
    entries = []
    [entries.extend(playerAnalysis.CSVMoves()) for playerAnalysis in playerAnalyses]
    writeClassifiedMovesCSV(entries)

  def classifyChunks(self, playerAnalyses):
    entries = []
    [entries.extend(playerAnalysis.CSVChunks()) for playerAnalysis in playerAnalyses]
    writeClassifiedChunksCSV(entries)

  def classifyMoveChunks(self, playerAnalyses):
    entries = []
    [entries.extend(playerAnalysis.CSVMoveChunks()) for playerAnalysis in playerAnalyses]
    writeClassifiedMoveChunksCSV(entries)

  def classifyGamePVs(self, playerAnalyses):
    entries = []
    [entries.extend(playerAnalysis.CSVGamePVs()) for playerAnalysis in playerAnalyses]
    writeClassifiedGamePVsCSV(entries)

  def classifyPlayerPVs(self, playerAnalyses):
    writeClassifiedPlayerPVsCSV([playerAnalysis.CSVPlayerPVs() for playerAnalysis in playerAnalyses])

  def classifyGames(self, playerAnalyses):
    writeClassifiedGamesCSV([playerAnalysis.CSVGames() for playerAnalysis in playerAnalyses])