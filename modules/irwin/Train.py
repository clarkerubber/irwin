import threading
import datetime
import time

from modules.irwin.updatePlayerEngineStatus import updatePlayerEngineStatus
from modules.irwin.TrainingStats import TrainingStats, Accuracy, Sample
from modules.irwin.writeCSV import writeClassifiedMovesCSV, writeClassifiedMoveChunksCSV

class Train(threading.Thread):
  def __init__(self, api, trainingStatsDB, playerAnalysisDB):
    threading.Thread.__init__(self)
    self.api = api
    self.trainingStatsDB = trainingStatsDB
    self.playerAnalysisDB = playerAnalysisDB

  def run(self):
    while True:
      if self.outOfDate():
        updatePlayerEngineStatus(self.api, self.playerAnalysisDB)
        sortedUsers = self.playerAnalysisDB.allSorted()
        sample = Sample(
          engines = sum(1 for user in sortedUsers if user.engine),
          legits = sum(1 for user in sortedUsers if not user.engine),
          unprocessed = self.playerAnalysisDB.countUnsorted())
        self.classifyMoves(sortedUsers)
        self.classifyMoveChunks(sortedUsers)
        self.trainingStatsDB.write(TrainingStats(
          date = datetime.datetime.utcnow(),
          accuracy = Accuracy(0, 0, 0, 0),
          sample = sample))
      time.sleep(10)

  def outOfDate(self):
    latest = self.trainingStatsDB.latest()
    if latest is not None:
      if datetime.datetime.utcnow() - latest.date > datetime.timedelta(days=1): # if it has been over a day since the last training
        return True
    else:
      return True
    return False

  def classifyMoves(self, playerAnalyses):
    entries = []
    [entries.extend(playerAnalysis.CSVMoves()) for playerAnalysis in playerAnalyses]
    writeClassifiedMovesCSV(entries)

  def classifyMoveChunks(self, playerAnalyses):
    entries = []
    [entries.extend(playerAnalysis.CSVChunks()) for playerAnalysis in playerAnalyses]
    writeClassifiedMoveChunksCSV(entries)
