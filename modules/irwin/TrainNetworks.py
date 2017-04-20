import threading

from modules.irwin.updatePlayerEngineStatus import updatePlayerEngineStatus
from modules.irwin.TrainingStats import TrainingStats, Accuracy, Sample
from modules.irwin.writeCSV import writeClassifiedMovesCSV, writeClassifiedMoveChunksCSV
from modules.irwin.MoveAssessment import MoveAssessment
from modules.irwin.ChunkAssessment import ChunkAssessment

class TrainNetworks(threading.Thread):
  def __init__(self, api, playerAnalysisDB):
    threading.Thread.__init__(self)
    self.api = api
    self.playerAnalysisDB = playerAnalysisDB

  def run(self):
    updatePlayerEngineStatus(self.api, self.playerAnalysisDB)
    sortedUsers = self.playerAnalysisDB.balancedSorted()
    sample = Sample(
      engines = sum(1 for user in sortedUsers if user.engine),
      legits = sum(1 for user in sortedUsers if not user.engine),
      unprocessed = self.playerAnalysisDB.countUnsorted())
    self.classifyMoves(sortedUsers)
    self.classifyMoveChunks(sortedUsers)
    MoveAssessment.learn()
    ChunkAssessment.learn()

  def classifyMoves(self, playerAnalyses):
    entries = []
    [entries.extend(playerAnalysis.CSVMoves()) for playerAnalysis in playerAnalyses]
    writeClassifiedMovesCSV(entries)

  def classifyMoveChunks(self, playerAnalyses):
    entries = []
    [entries.extend(playerAnalysis.CSVChunks()) for playerAnalysis in playerAnalyses]
    writeClassifiedMoveChunksCSV(entries)
