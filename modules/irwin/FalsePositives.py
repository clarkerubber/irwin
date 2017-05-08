from collections import namedtuple
import datetime

FalsePositive = namedtuple('FalsePositive', ['id', 'activation'])
FalsePositives = namedtuple('FalsePositives', ['falsePositives'])

class FalsePositiveBSONHandler:
  @staticmethod
  def reads(bson):
    return FalsePositive(bson['id'], bson['activation'])

  @staticmethod
  def writes(falsePositive):
    return {
      'id': falsePositive.id,
      'activation': falsePositive.activation
    }

class FalsePositivesBSONHandler:
  @staticmethod
  def reads(bson):
    return FalsePositives([FalsePositiveBSONHandler.reads(fp) for fp in bson['falsePositives']])

  @staticmethod
  def writes(falsePositives):
    return {
      'falsePositives': [FalsePositiveBSONHandler.writes(fp) for fp in falsePositives.falsePositives],
      'date': datetime.datetime.utcnow()
    }

class FalsePositivesDB(namedtuple('FalsePositivesDB', ['falsePositivesColl'])):
  def write(self, falsePositives):
    self.falsePositivesColl.insert_one(FalsePositivesBSONHandler.writes(falsePositives))