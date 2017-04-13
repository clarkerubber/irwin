from collections import namedtuple

IrwinReport = namedtuple('IrwinReport', ['activation', 'decision'])

class IrwinReportBSONHandler:
  @staticmethod
  def reads(bson):
    return IrwinReport(**bson)

  @staticmethod
  def writes(irwinReport):
    return irwinReport._asdict()