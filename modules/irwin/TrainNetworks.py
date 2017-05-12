import threading

from modules.irwin.updatePlayerEngineStatus import updatePlayerEngineStatus
from modules.irwin.writeCSV import writeClassifiedMovesCSV, writeClassifiedMoveChunksCSV, writeClassifiedPVsCSV, writeClassifiedPVsDrawishCSV, writeClassifiedPVsLosingCSV, writeClassifiedPVsOverallCSV
from modules.irwin.MoveAssessment import MoveAssessment
from modules.irwin.ChunkAssessment import ChunkAssessment
from modules.irwin.PVAssessment import PVAssessment
from modules.irwin.PVDrawAssessment import PVDrawAssessment
from modules.irwin.PVLosingAssessment import PVLosingAssessment
from modules.irwin.PVOverallAssessment import PVOverallAssessment

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
      sortedUsers = self.playerAnalysisDB.balancedSorted()
      self.classifyMoves(sortedUsers)
      self.classifyMoveChunks(sortedUsers)
      self.classifyPVs(sortedUsers)
      self.classifyPVsDrawish(sortedUsers)
      self.classifyPVsLosing(sortedUsers)
      self.classifyPVsOverall(sortedUsers)
      MoveAssessment.learn(self.minTrainingSteps, self.incTrainingSteps)
      ChunkAssessment.learn(self.minTrainingSteps, self.incTrainingSteps)
      PVAssessment.learn(self.minTrainingSteps, self.incTrainingSteps)
      PVDrawAssessment.learn(self.minTrainingSteps, self.incTrainingSteps)
      PVLosingAssessment.learn(self.minTrainingSteps, self.incTrainingSteps)
      PVOverallAssessment.learn(self.minTrainingSteps, self.incTrainingSteps)

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

  def classifyPVsDrawish(self, playerAnalyses):
    entries = []
    [entries.append(playerAnalysis.CSVPVsDrawish()) for playerAnalysis in playerAnalyses]
    writeClassifiedPVsDrawishCSV(entries)

  def classifyPVsLosing(self, playerAnalyses):
    entries = []
    [entries.append(playerAnalysis.CSVPVsLosing()) for playerAnalysis in playerAnalyses]
    writeClassifiedPVsLosingCSV(entries)

  def classifyPVsOverall(self, playerAnalyses):
    entries = []
    [entries.append(playerAnalysis.CSVPVsOverall()) for playerAnalysis in playerAnalyses if playerAnalysis.CSVPVsOverall() is not None]
    writeClassifiedPVsOverallCSV(entries)