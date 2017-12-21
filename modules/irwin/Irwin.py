from pprint import pprint
from random import shuffle

import logging
import numpy as np
import os.path

from modules.irwin.BinaryGameModel import BinaryGameModel
from modules.irwin.PlayerModel import PlayerModel

from modules.irwin.PlayerGameActivations import PlayerGameActivations

from modules.irwin.ConfidentGameAnalysisPivot import ConfidentGameAnalysisPivot, ConfidentGameAnalysisPivotDB

from modules.core.GameAnalysisStore import GameAnalysisStore

class Irwin():
  def __init__(self, env, config):
    self.env = env
    self.config = config
    self.generalGameModel = BinaryGameModel(env, 'general')
    self.narrowGameModel = BinaryGameModel(env, 'narrow')
    self.playerModel = PlayerModel(env)

  def getEvaluationDataset(self, batchSize):
    print("getting players", end="...", flush=True)
    players = self.env.playerDB.balancedSample(batchSize)
    print(" %d" % len(players))
    print("getting game analyses")
    analysesByPlayer = [(player, [ga for ga in self.env.gameAnalysisDB.byUserId(player.id) if len(ga.moveAnalyses) < 60]) for player in players]
    return analysesByPlayer

  def evaluate(self):
    print("evaluate model")
    print("getting model")
    gameModel = self.narrowGameModel.model()
    playerModel = self.playerModel.model()
    print("getting dataset")
    analysesByPlayer = self.getEvaluationDataset(self.config['evalSize'])
    activations = [self.activation(self.predict([ga.moveAnalysisTensors() for ga in gameAnalyses[1]], gameModel), playerModel) for gameAnalyses in analysesByPlayer]
    outcomes = list(zip(analysesByPlayer, [Irwin.outcome(a, 90, ap[0].engine) for ap, a in zip(analysesByPlayer, activations)]))
    tp = len([a for a in outcomes if a[1] == 1])
    fn = len([a for a in outcomes if a[1] == 2])
    tn = len([a for a in outcomes if a[1] == 3])
    fp = len([a for a in outcomes if a[1] == 4])

    fpnames = [a[0][0].id for a in outcomes if a[1] == 4]

    print("True positive: " + str(tp))
    print("False negative: " + str(fn))
    print("True negative: " + str(tn))
    print("False positive: " + str(fp))

    pprint(fpnames)

  def buildPivotTable(self):
    return True #stub

  def buildConfidenceTable(self):
    cheatGameAnalyses = []
    legitGameAnalyses = []
    for length in range(20, 60):
      print("getting games of length: " + str(length))
      cheatPivotEntries = self.env.gameAnalysisPlayerPivotDB.byEngineAndLength(True, length)
      legitPivotEntries = self.env.gameAnalysisPlayerPivotDB.byEngineAndLength(False, length)

      cheatGameAnalyses.extend(self.env.gameAnalysisDB.byIds([cpe.id for cpe in cheatPivotEntries]))
      legitGameAnalyses.extend(self.env.gameAnalysisDB.byIds([lpe.id for lpe in legitPivotEntries]))

    model = self.narrowGameModel.model()

    print("getting moveAnalysisTensors")
    cheatTensors = [tga.moveAnalysisTensors() for tga in cheatGameAnalyses]
    legitTensors = [tga.moveAnalysisTensors() for tga in legitGameAnalyses]

    print("predicting the things")
    cheatGamePredictions = self.predict(cheatTensors, model)
    legitGamePredictions = self.predict(legitTensors, model)

    confidentCheats = [ConfidentGameAnalysisPivot.fromGamesAnalysisandPrediction(gameAnalysis, prediction[0], engine=True) for gameAnalysis, prediction in zip(cheatGameAnalyses, cheatGamePredictions)]
    confidentLegits = [ConfidentGameAnalysisPivot.fromGamesAnalysisandPrediction(gameAnalysis, prediction[0], engine=False) for gameAnalysis, prediction in zip(legitGameAnalyses, legitGamePredictions)]

    print("writing to db")
    self.env.confidentGameAnalysisPivotDB.lazyWriteMany(confidentCheats + confidentLegits)

  def buildPlayerGameActivationsTable(self, model=None):
    if model is None:
      print("using default model")
      model = self.narrowGameModel.model()
    print("getting players")
    engines = self.env.playerDB.byEngine(True)
    legits = self.env.playerDB.byEngine(False)

    print("got " + str(len(engines + legits)) + " players")

    playerGameActivations = []

    for player in engines + legits:
      print("predicting " + player.id)
      gs = GameAnalysisStore.new()
      gs.addGameAnalyses(self.env.gameAnalysisDB.byUserId(player.id))
      predictions = self.predict(gs.gameAnalysisTensors(), model)
      playerGameActivations.append(PlayerGameActivations(player.id, player.engine, [int(100*np.asscalar(p[0][0][0])) for p in predictions]))

    print("writing to DB")
    self.env.playerGameActivationsDB.lazyWriteMany(playerGameActivations)

  @staticmethod
  def outcome(a, t, e): # activation, threshold, expected value
    if a > t and e:
      return 1 # true positive
    if a <= t and e:
      return 2 # false negative
    if a <= t and not e:
      return 3 # true negative
    else:
      return 4 # false positive

  def predict(self, tensors, model=None):
    if model == None:
      model = self.narrowGameModel.model()

    pvs =         [[m[0] for m in p][:40] for p in tensors]
    moveStats =   [[m[1] for m in p][:40] for p in tensors]
    moveNumbers = [[m[2] for m in p][:40] for p in tensors]
    ranks =       [[m[3] for m in p][:40] for p in tensors]
    advs =        [[m[4] for m in p][:40] for p in tensors]
    ambs =        [[m[5] for m in p][:40] for p in tensors]

    predictions = []
    for p, m, mn, r, a, am in zip(pvs, moveStats, moveNumbers, ranks, advs, ambs):
      predictions.append(model.predict([np.array([p]), np.array([m]), np.array([mn]), np.array([r]), np.array([a]), np.array([am])]))

    return predictions

  def report(self, userId, gameAnalysisStore, gameModel=None, playerModel=None):
    predictions = self.predict(gameAnalysisStore.gameAnalysisTensors(), gameModel)
    report = {
      'userId': userId,
      'activation': self.activation(predictions, playerModel),
      'games': [Irwin.gameReport(ga, p) for ga, p in zip(gameAnalysisStore.gameAnalyses, predictions)]
    }
    return report

  def activation(self, predictions, playerModel=None): # determined using the player model
    return self.playerModel.predict([int(100*np.asscalar(prediction[0][0][0])) for prediction in predictions], playerModel) # multiply entry amount by weight

  @staticmethod
  def gameReport(gameAnalysis, prediction):
    return {
      'gameId': gameAnalysis.gameId,
      'activation': int(100*prediction[0][0][0]),
      'moves': [Irwin.moveReport(am, p) for am, p in zip(gameAnalysis.moveAnalyses, list(prediction[1][0]))]
    }

  @staticmethod
  def moveReport(analysedMove, prediction):
    return {
      'a': int(100*prediction[0]),
      'r': analysedMove.trueRank(),
      'm': analysedMove.ambiguity(),
      'o': int(100*analysedMove.advantage()),
      'l': int(100*analysedMove.winningChancesLoss())
    }

  @staticmethod
  def getGameEngineStatus(gameAnalysis, players):
    return any([p for p in players if gameAnalysis.userId == p.id and p.engine])

  @staticmethod
  def assignLabels(gameAnalyses, players):
    return [int(Irwin.getGameEngineStatus(gameAnalysis, players)) for gameAnalysis in gameAnalyses]

  @staticmethod
  def flatten(l):
    return [item for sublist in l for item in sublist]