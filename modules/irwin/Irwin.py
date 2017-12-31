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
    analysesByPlayer = [(player, GameAnalysisStore([], [ga for ga in self.env.gameAnalysisDB.byUserId(player.id) if len(ga.moveAnalyses) < 50])) for player in players]
    return analysesByPlayer

  def evaluate(self):
    print("evaluate model")
    print("getting model")
    generalModel = self.generalGameModel.model()
    narrowModel = self.narrowGameModel.model()
    playerModel = self.playerModel.model()
    print("getting dataset")
    analysisStoreByPlayer = self.getEvaluationDataset(self.config['evalSize'])
    activations = [self.activation(self.predict(gameAnalysisStore.quickGameAnalysisTensors(), generalModel, narrowModel), gameAnalysisStore.playerTensor(), playerModel) for player, gameAnalysisStore in analysisStoreByPlayer]
    outcomes = list(zip(analysisStoreByPlayer, [Irwin.outcome(a, 90, ap[0].engine) for ap, a in zip(analysisStoreByPlayer, activations)]))
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
    print("getting games")
    cheatPivotEntries = self.env.gameAnalysisPlayerPivotDB.byEngine(True)
    legitPivotEntries = self.env.gameAnalysisPlayerPivotDB.byEngine(False)

    cheatGameAnalyses = self.env.gameAnalysisDB.byIds([cpe.id for cpe in cheatPivotEntries])
    legitGameAnalyses = self.env.gameAnalysisDB.byIds([lpe.id for lpe in legitPivotEntries])

    model = self.generalGameModel.model()

    print("getting moveAnalysisTensors")
    cheatTensors = [tga.moveAnalysisTensors() for tga in cheatGameAnalyses]
    legitTensors = [tga.moveAnalysisTensors() for tga in legitGameAnalyses]

    print("predicting the things")
    cheatGamePredictions = self.predict(cheatTensors, model, generalOnly=True)
    legitGamePredictions = self.predict(legitTensors, model, generalOnly=True)

    confidentCheats = [ConfidentGameAnalysisPivot.fromGamesAnalysisandPrediction(gameAnalysis, prediction[0][0], engine=True) for gameAnalysis, prediction in zip(cheatGameAnalyses, cheatGamePredictions)]
    confidentLegits = [ConfidentGameAnalysisPivot.fromGamesAnalysisandPrediction(gameAnalysis, prediction[0][0], engine=False) for gameAnalysis, prediction in zip(legitGameAnalyses, legitGamePredictions)]

    print("writing to db")
    self.env.confidentGameAnalysisPivotDB.lazyWriteMany(confidentCheats + confidentLegits)

  def buildPlayerGameActivationsTable(self, generalModel=None, narrowModel=None):
    if generalModel is None:
      generalModel = self.generalGameModel.model()
    if narrowModel is None:
      narrowModel = self.narrowGameModel.model()
    print("getting players")
    engines = self.env.playerDB.byEngine(True)
    legits = self.env.playerDB.byEngine(False)

    amount = len(engines+legits)

    print("got " + str(amount) + " players")

    playerGameActivations = []

    for i, player in enumerate(engines + legits):
      print("predicting " + str(i) + '/' + str(amount) + ' ' + player.id)
      gs = GameAnalysisStore.new()
      gs.addGameAnalyses(self.env.gameAnalysisDB.byUserId(player.id))
      predictions = self.predict(gs.gameAnalysisTensors(), generalModel, narrowModel)
      pga = PlayerGameActivations(
        player.id, player.engine, 
        [int(100*(np.asscalar(p[0][0][0][0]))) for p in predictions],
        [int(100*(np.asscalar(p[1][0][0][0]))) for p in predictions])
      pprint(pga)
      self.env.playerGameActivationsDB.write(pga)

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

  def predict(self, tensors, generalModel=None, narrowModel=None, generalOnly=False):
    if generalModel == None:
      generalModel = self.generalGameModel.model()

    if narrowModel == None and generalOnly == False:
      narrowModel = self.narrowGameModel.model()

    pvs =         [[m[0] for m in p][:40] for p in tensors]
    moveStats =   [[m[1] for m in p][:40] for p in tensors]
    moveNumbers = [[m[2] for m in p][:40] for p in tensors]
    ranks =       [[m[3] for m in p][:40] for p in tensors]
    advs =        [[m[4] for m in p][:40] for p in tensors]
    ambs =        [[m[5] for m in p][:40] for p in tensors]

    predictions = []
    if not generalOnly:
      for p, m, mn, r, a, am in zip(pvs, moveStats, moveNumbers, ranks, advs, ambs):
        predictions.append((
          generalModel.predict([np.array([p]), np.array([m]), np.array([mn]), np.array([r]), np.array([a]), np.array([am])]),
          narrowModel.predict([np.array([p]), np.array([m]), np.array([mn]), np.array([r]), np.array([a]), np.array([am])])
        ))
    else:
      for p, m, mn, r, a, am in zip(pvs, moveStats, moveNumbers, ranks, advs, ambs):
        predictions.append((
          generalModel.predict([np.array([p]), np.array([m]), np.array([mn]), np.array([r]), np.array([a]), np.array([am])]),
          []
        ))
    return predictions

  def report(self, userId, gameAnalysisStore, generalModel=None, narrowModel=None, playerModel=None):
    predictions = self.predict(gameAnalysisStore.gameAnalysisTensors(), generalModel, narrowModel)
    report = {
      'userId': userId,
      'activation': self.activation(predictions, gameAnalysisStore.playerTensor(), playerModel),
      'games': [Irwin.gameReport(ga, p) for ga, p in zip(gameAnalysisStore.gameAnalyses, predictions)]
    }
    return report

  def activation(self, predictions, playerTensor, playerModel=None): # determined using the player model
    p = self.playerModel.predict(
      [int(100*np.asscalar(prediction[0][0][0])) for prediction in predictions],
      [int(100*np.asscalar(prediction[1][0][0])) for prediction in predictions],
      playerTensor,
      playerModel)
    if len(predictions) < 5:
      return min(p, 80)
    return p

  @staticmethod
  def gameReport(gameAnalysis, prediction):
    return {
      'gameId': gameAnalysis.gameId,
      'activation': int(50*(prediction[0][0][0][0] + prediction[1][0][0][0])),
      'moves': [Irwin.moveReport(am, p) for am, p in zip(gameAnalysis.moveAnalyses, zip(list(prediction[0][1][0]), list(prediction[1][1][0])))]
    }

  @staticmethod
  def moveReport(analysedMove, prediction):
    return {
      'a': int(50*(prediction[0][0] + prediction[1][0])),
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