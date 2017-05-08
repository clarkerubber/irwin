import threading

from modules.irwin.updatePlayerEngineStatus import updatePlayerEngineStatus
from modules.irwin.writeCSV import writeClassifiedMovesCSV, writeClassifiedMoveChunksCSV, writeClassifiedPVsCSV
from modules.irwin.MoveAssessment import MoveAssessment
from modules.irwin.ChunkAssessment import ChunkAssessment
from modules.irwin.PVAssessment import PVAssessment

class TrainNetworks(threading.Thread):
  def __init__(self, api, playerAnalysisDB, minTrainingSteps, incTrainingSteps, updateAll):
    threading.Thread.__init__(self)
    self.api = api
    self.playerAnalysisDB = playerAnalysisDB
    self.minTrainingSteps = minTrainingSteps
    self.incTrainingSteps = incTrainingSteps
    self.updateAll = updateAll

  def run(self):
    updatePlayerEngineStatus(self.api, self.playerAnalysisDB, self.updateAll)
    sortedUsers = self.playerAnalysisDB.balancedSorted()
    self.classifyMoves(sortedUsers)
    self.classifyMoveChunks(sortedUsers)
    self.classifyPVs(sortedUsers)
    MoveAssessment.learn(self.minTrainingSteps, self.incTrainingSteps)
    ChunkAssessment.learn(self.minTrainingSteps, self.incTrainingSteps)
    PVAssessment.learn(self.minTrainingSteps, self.incTrainingSteps)

  def classifyMoves(self, playerAnalyses):
    entries = []
    [entries.extend(playerAnalysis.CSVMoves()) for playerAnalysis in playerAnalyses]
    writeClassifiedMovesCSV(entries)

  def classifyMoveChunks(self, playerAnalyses):
    entries = []
    [entries.extend(playerAnalysis.CSVChunks()) for playerAnalysis in playerAnalyses]
    writeClassifiedMoveChunksCSV(entries)

  def classifyPVs(self, playerAnalyses):
    entries = []
    [entries.append(playerAnalysis.CSVPVs()) for playerAnalysis in playerAnalyses]
    writeClassifiedPVsCSV(entries)