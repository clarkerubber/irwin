from collections import namedtuple

import datetime
import pymongo

Accuracy = namedtuple('Accuracy', ['truePositive', 'falsePositive', 'trueNegative', 'falseNegative'])
Sample = namedtuple('Sample', ['cheaters', 'legits'])

TrainingStats = namedtuple('TrainingStats', ['date', 'accuracy', 'sample'])

class TrainingStatsBSONHandler:
  @staticmethod
  def reads(bson):
    return TrainingStats(
      date = bson['date'],
      accuracy = Accuracy(**bson['accuracy']),
      sample = Sample(**bson['sample'])
    )

  @staticmethod
  def writes(trainingStats):
    return {
      'date': trainingStats.date,
      'accuracy': trainingStats.accuracy._asdict(),
      'sample': trainingStats.sample._asdict()
    }

class TrainingStatsDB(namedtuple('TrainingStatsDB', ['trainingStatsColl'])):
  def latest(self):
    return TrainingStatsBSONHandler.reads(next(self.trainingStatsColl.find().sort('date', pymongo.DESCENDING), None))

  def write(self, trainingStats):
    self.trainingStatsColl.insert_one(TrainingStatsBSONHandler.writes(trainingStats))