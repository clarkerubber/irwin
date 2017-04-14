from collections import namedtuple

from modules.irwin.updatePlayerAnalysisResults import updatePlayerAnalysisResults
from modules.irwin.TrainingStats import TrainingStats, Accuracy, Sample

import datetime

class Irwin(namedtuple('Irwin', ['env'])):
  # Core methods
  def outOfDate(self):
    latest = self.env.trainingStatsDB.latest()
    if latest is not None:
      if datetime.datetime.utcnow() - latest.date > datetime.timedelta(days=1): # if it has been over a day since the last training
        return True
    else:
      return True
    return False

  def updateDataset(self):
    if self.outOfDate():
      updatePlayerAnalysisResults(self.env.api, self.env.playerAnalysisDB)
      self.env.trainingStatsDB.write(
        TrainingStats(
          date = datetime.datetime.utcnow(),
          accuracy = Accuracy(0, 0, 0, 0),
          sample = Sample(0, 0)))