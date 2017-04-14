from collections import namedtuple

from modules.irwin.updatePlayerAnalysisResults import updatePlayerAnalysisResults
from modules.irwin.TrainingStats import TrainingStats, Accuracy, Sample

import datetime

class Irwin(namedtuple('Irwin', ['api', 'trainingStatsDB', 'playerAnalysisDB'])):
  def outOfDate(self):
    latest = self.trainingStatsDB.latest()
    if latest is not None:
      if datetime.datetime.utcnow() - latest.date > datetime.timedelta(days=1): # if it has been over a day since the last training
        return True
    else:
      return True
    return False

  def updateDataset(self):
    if self.outOfDate():
      sample = updatePlayerAnalysisResults(self.api, self.playerAnalysisDB)
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