import threading

from modules.irwin.updatePlayerEngineStatus import updatePlayerEngineStatus
from modules.irwin.writeCSV import writeClassifiedMovesCSV, writeClassifiedMoveChunksCSV, writeClassifiedGamesCSV, writeClassifiedPlayersCSV
from modules.irwin.MoveAssessment import MoveAssessment
from modules.irwin.ChunkAssessment import ChunkAssessment
from modules.irwin.GameAssessment import GameAssessment

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
      #updatePlayerEngineStatus(self.api, self.playerAnalysisDB, self.updateAll)
      #sortedUsers = self.playerAnalysisDB.balancedSorted()
      #self.classifyMoves(sortedUsers)
      #self.classifyMoveChunks(sortedUsers)
      #self.classifyGames(sortedUsers)
      #MoveAssessment.learn(self.minTrainingSteps, self.incTrainingSteps)
      #ChunkAssessment.learn(self.minTrainingSteps, self.incTrainingSteps)
      GameAssessment.learn(self.minTrainingSteps, self.incTrainingSteps)

  def classifyMoves(self, playerAnalyses):
    entries = []
    [entries.extend(playerAnalysis.CSVMoves()) for playerAnalysis in playerAnalyses]
    writeClassifiedMovesCSV(entries)

  def classifyMoveChunks(self, playerAnalyses):
    entries = []
    [entries.extend(playerAnalysis.CSVChunks()) for playerAnalysis in playerAnalyses]
    writeClassifiedMoveChunksCSV(entries)

  def classifyGames(self, playerAnalyses):
    entries = []
    [entries.extend(playerAnalysis.CSVGames()) for playerAnalysis in playerAnalyses]
    writeClassifiedGamesCSV(entries)

  def classifyPlayers(self, playerAnalyses):
    writeClassifiedPlayersCSV([playerAnalysis.CSVPlayer() for playerAnalysis in playerAnalyses])