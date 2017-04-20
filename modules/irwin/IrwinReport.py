from collections import namedtuple

class IrwinReport:
  def __init__(self, activation):
    self.activation = activation
    self.decision = activation > 50

  def __str__(self):
    return 'IrwinReport('+str(self.activation)+', '+str(self.decision)+')'

class IrwinReportBSONHandler:
  @staticmethod
  def reads(activation):
    return IrwinReport(activation)

  @staticmethod
  def writes(irwinReport):
    return irwinReport.activation