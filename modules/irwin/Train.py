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
        sample = Sample(engines = sum(1 for user in sortedUsers if user.engine), legits = sum(1 for user in sortedUsers if not user.engine))
        self.classifyMoves(sortedUsers)
        self.classifiyMoveChunks(sortedUsers)
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
        for moveAnalysis in gameAnalysis.analysedMoves:
          entries.append({
            'engine': playerAnalysis.engine,
            'titled': playerAnalysis.titled,
            'moveNumber': moveAnalysis.move,
            'rank': moveAnalysis.rank(),
            'loss': moveAnalysis.winningChancesLoss(),
            'advantage': moveAnalysis.advantage(),
            'ambiguity': moveAnalysis.ambiguity(),
            'timeConsistent': gameAnalysis.consistentMoveTime(moveAnalysis.move),
            'bot': gameAnalysis.playerAssessment.hold,
            'blurs': gameAnalysis.playerAssessment.blurs
          })
    writeClassifiedMovesCSV(entries)

  def classifyMoveChunks(self, playerAnalyses):
    entries = []
    for playerAnalysis in playerAnalyses:
      for gameAnalysis in playerAnalysis.gameAnalyses.gameAnalyses:
        for i in range(len(gameAnalysis.analysedMoves) - 9): # assume the length of the game is > 10
          entry = [
            playerAnalysis.engine,
            playerAnalysis.titled,
            gameAnalysis.playerAssessment.bot,
            gameAnalysis.playerAssessment.blurs,
            i]
          for analysedMove in gameAnalysis.analysedMoves[i:i+10]:
            entry.extend([
              analysedMove.rank(),
              analysedMove.winningChancesLoss(),
              analysedMove.advantage(),
              analysedMove.ambiguity(),
              analysedMove.timeConsistent()
            ])
          entries.append(entry)
    writeClassifiedMoveChunksCSV(entries)
