import threading
import datetime
import time

from modules.irwin.updatePlayerEngineStatus import updatePlayerEngineStatus
from modules.irwin.TrainingStats import TrainingStats, Accuracy, Sample
from modules.irwin.writeCSV import writeCSV

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
        sample = self.classifyMoves(sortedUsers)
        self.trainingStatsDB.write(
          TrainingStats(
            date = datetime.datetime.utcnow(),
            accuracy = Accuracy(0, 0, 0, 0),
            sample = sample))
      time.sleep(10)

  def outOfDate(self):
    latest = self.trainingStatsDB.latest()
    if latest is not None:
      if datetime.datetime.utcnow() - latest.date > datetime.timedelta(hours=1): # if it has been over a day since the last training
        return True
    else:
      return True
    return False

  def classifyMoves(self, playerAnalyses):
    entries = []
    for playerAnalysis in playerAnalyses:
      for gameAnalysis in playerAnalysis.gameAnalyses.gameAnalyses:
        for moveAnalysis in gameAnalysis.movesForAssessment():
          entries.append({
            'engine': playerAnalysis.engine,
            'titled': playerAnalysis.titled,
            'moveNumber': moveAnalysis.move,
            'rank': moveAnalysis.rank(),
            'loss': moveAnalysis.winningChancesLoss(),
            'advantage': moveAnalysis.advantage(),
            'ambiguous': moveAnalysis.ambiguous(),
            'timeConsistent': gameAnalysis.consistentMoveTime(moveAnalysis.move),
            'bot': gameAnalysis.playerAssessment.hold,
            'blurs': gameAnalysis.playerAssessment.blurs
          })
    writeCSV(entries)
    return Sample(engines = sum(1 if playerAnalysis.engine else 0 for playerAnalysis in playerAnalyses),
      legits = sum(0 if playerAnalysis.engine else 1 for playerAnalysis in playerAnalyses))