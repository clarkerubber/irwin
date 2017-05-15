from collections import namedtuple
import datetime

FalseReport = namedtuple('FalseReport', ['id', 'activation'])
FalsePositives = namedtuple('FalseReports', ['falsePositives', 'falseNegatives'])

class FalseReportBSONHandler:
  @staticmethod
  def reads(bson):
    return FalseReport(bson['id'], bson['activation'])

  @staticmethod
  def writes(falsePositive):
    return {
      'id': falsePositive.id,
      'activation': falsePositive.activation
    }

class FalseReportsBSONHandler:
  @staticmethod
  def reads(bson):
    return FalseReports(
      falsePositives = [FalseReportBSONHandler.reads(fp) for fp in bson['falsePositives']],
      falseNegatives = [FalseReportBSONHandler.reads(fn) for fn in bson['falseNegatives']])

  @staticmethod
  def writes(falseReports):
    return {
      'falsePositives': [FalseReportBSONHandler.writes(fp) for fp in falseReports.falsePositives],
      'falseNegatives': [FalseReportBSONHandler.writes(fn) for fn in falseReports.falseNegatives]
      'date': datetime.datetime.utcnow()
    }

class FalseReportsDB(namedtuple('FalseReportsDB', ['falseReportsColl'])):
  def write(self, falseReports):
    self.falseReportsColl.insert_one(FalseReportsBSONHandler.writes(falseReports))