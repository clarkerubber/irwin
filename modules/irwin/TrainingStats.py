from collections import namedtuple

import pymongo

Accuracy = namedtuple('Accuracy', ['truePositive', 'falsePositive', 'trueNegative', 'falseNegative', 'indecise'])
Sample = namedtuple('Sample', ['engines', 'legits', 'unprocessed'])

TrainingStats = namedtuple('TrainingStats', ['date', 'accuracy', 'sample'])

class TrainingStatsBSONHandler:
  @staticmethod
  def reads(bson):
    return TrainingStats(
      date = bson['date'],
      accuracy = Accuracy(
        truePositive = bson['accuracy'].get('truePositive', 0),
        falsePositive = bson['accuracy'].get('falsePositive', 0),
        trueNegative = bson['accuracy'].get('trueNegative', 0),
        falseNegative = bson['accuracy'].get('falseNegative', 0),
        indecise = bson['accuracy'].get('indecise', 0)
      ),
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
    trainingStatsBSON = next(self.trainingStatsColl.find().sort('date', pymongo.DESCENDING), None)
    if trainingStatsBSON is not None:
      return TrainingStatsBSONHandler.reads(trainingStatsBSON)
    return None

  def write(self, trainingStats):
    self.trainingStatsColl.insert_one(TrainingStatsBSONHandler.writes(trainingStats))