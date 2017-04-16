from collections import namedtuple
import threading

from modules.irwin.Train import Train

class Irwin(namedtuple('Irwin', ['api', 'learner', 'trainingStatsDB', 'playerAnalysisDB'])):
  def train(self):
    if self.learner == 1:
      Train(self.api, self.trainingStatsDB, self.playerAnalysisDB).start()

  def assessMove(self, gameAnalysis, analysedMove): # Pass move to neural network and assess it.
    pass

  def assessGame(self, gameAnalysis):
    [self.assessMove(gameAnalysis, analysedMove) for analysedMove in gameAnalysis.analysedMoves]

  def assessPlayer(self, playerAnalysis):
    [self.assessGame(gameAnalysis) for gameAnalysis in playerAnalysis.gameAnalyses]