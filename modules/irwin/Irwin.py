from collections import namedtuple
import threading
import datetime
import time

from modules.irwin.TrainNetworks import TrainNetworks
from modules.irwin.MoveAssessment import MoveAssessment
from modules.irwin.ChunkAssessment import ChunkAssessment
from modules.core.AssessedMove import AssessedMove
from modules.core.AssessedChunk import AssessedChunk
from modules.core.PlayerAnalysis import PlayerAnalysis

class Irwin(namedtuple('Irwin', ['api', 'learner', 'trainingStatsDB', 'playerAnalysisDB'])):
  def train(self): # runs forever
    if self.learner == 1:
      TrainAndEvaluate(self.api, self.trainingStatsDB, self.playerAnalysisDB).start()

  @staticmethod
  def assessGame(gameAnalysis, titled):
    gameAnalysis.assessedMoves = [AssessedMove(analysedMove, irwinReport) for analysedMove, irwinReport in zip(gameAnalysis.analysedMoves, MoveAssessment.applyNet(gameAnalysis.tensorInputMoves(titled)))]
    gameAnalysis.assessedChunks = [AssessedChunk(move, irwinReport) for move, irwinReport in enumerate(ChunkAssessment.applyNet(gameAnalysis.tensorInputChunks(titled)))]
    return gameAnalysis

  @staticmethod
  def assessPlayer(playerAnalysis):
    return PlayerAnalysis(
      id = playerAnalysis.id,
      titled = playerAnalysis.titled,
      engine = playerAnalysis.engine,
      gamesPlayed = playerAnalysis.gamesPlayed,
      closedReports = playerAnalysis.closedReports,
      gameAnalyses = [Irwin.assessGame(gameAnalysis, playerAnalysis.titled) for gameAnalysis in playerAnalysis.gameAnalyses.gameAnalyses]
      )
    

class TrainAndEvaluate(threading.Thread):
  def __init__(self, api, trainingStatsDB, playerAnalysisDB):
    threading.Thread.__init__(self)
    self.api = api
    self.trainingStatsDB = trainingStatsDB
    self.playerAnalysisDB = playerAnalysisDB

  def run(self):
    while True:
      time.sleep(10)
      if self.outOfDate():
        trainer = TrainNetworks(self.api, self.playerAnalysisDB)
        trainer.start()
        trainer.join()
        engines = self.playerAnalysisDB.engines()
        legits = self.playerAnalysisDB.legits()
        engines = [Irwin.assessPlayer(engine) for engine in engines]
        legits = [Irwin.assessPlayer(legit) for legit in legits]


  def outOfDate(self):
    latest = self.trainingStatsDB.latest()
    if latest is not None:
      if datetime.datetime.utcnow() - latest.date > datetime.timedelta(days=1): # if it has been over a day since the last training
        return True
    else:
      return True
    return False