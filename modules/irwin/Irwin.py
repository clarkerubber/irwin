from collections import namedtuple

from modules.irwin.updatePlayerEngineStatus import updatePlayerEngineStatus
from modules.irwin.TrainingStats import TrainingStats, Accuracy, Sample
from modules.irwin.writeCSV import writeCSV

import datetime

class Irwin(namedtuple('Irwin', ['api', 'trainingStatsDB', 'playerAnalysisDB'])):
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

  def updateDataset(self):
    if self.outOfDate():
      updatePlayerEngineStatus(self.api, self.playerAnalysisDB)
      sortedUsers = self.playerAnalysisDB.allSorted()
      sample = self.classifyMoves(sortedUsers)
      self.trainingStatsDB.write(
        TrainingStats(
          date = datetime.datetime.utcnow(),
          accuracy = Accuracy(0, 0, 0, 0),
          sample = sample))

  def assessMove(self, gameAnalysis, analysedMove): # Pass move to neural network and assess it.
    pass

  def assessGame(self, gameAnalysis):
    [self.assessMove(gameAnalysis, analysedMove) for analysedMove in gameAnalysis.analysedMoves]

  def assessPlayer(self, playerAnalysis):
    [self.assessGame(gameAnalysis) for gameAnalysis in playerAnalysis.gameAnalyses]