from pprint import pprint
from random import shuffle

import logging
import numpy as np
import os.path

from modules.irwin.AnalysedGameModel import AnalysedGameModel
from modules.irwin.GameModel import GameModel
from modules.irwin.PlayerModel import PlayerModel

from modules.irwin.PlayerGameActivations import PlayerGameActivations

from modules.irwin.ConfidentGameAnalysisPivot import ConfidentGameAnalysisPivot, ConfidentGameAnalysisPivotDB

from modules.core.GameAnalysisStore import GameAnalysisStore

class Irwin():
  def __init__(self, env, config):
    self.env = env
    self.config = config
    self.gameModel = GameModel(env)
    self.generalGameModel = AnalysedGameModel(env, 'general')
    self.narrowGameModel = AnalysedGameModel(env, 'narrow')
    self.playerModel = PlayerModel(env)

  def getEvaluationDataset(self, batchSize):
    print("getting players", end="...", flush=True)
    players = self.env.playerDB.balancedSample(batchSize)
    print(" %d" % len(players))
    print("getting game analyses")
    analysesByPlayer = [(player, GameAnalysisStore([], [ga for ga in self.env.gameAnalysisDB.byUserId(player.id)])) for player in players]
    return analysesByPlayer

  def evaluate(self):
    print("evaluate model")
    print("getting dataset")
    analysisStoreByPlayer = self.getEvaluationDataset(self.config['evalSize'])
    activations = [
      self.activation(
        PlayerGameActivations.fromTensor(
          player.id,
          player.engine,
          self.predict(
            gameAnalysisStore.quickGameAnalysisTensors())),
        gameAnalysisStore.playerTensor()) for player, gameAnalysisStore in analysisStoreByPlayer]
    outcomes = list(zip(analysisStoreByPlayer, [Irwin.outcome(a, 90, 60, ap[0].engine) for ap, a in zip(analysisStoreByPlayer, activations)]))
    tp = len([a for a in outcomes if a[1] == 1])
    fn = len([a for a in outcomes if a[1] == 2])
    tn = len([a for a in outcomes if a[1] == 3])
    fp = len([a for a in outcomes if a[1] == 4])
    tr = len([a for a in outcomes if a[1] == 5])
    fr = len([a for a in outcomes if a[1] == 6])

    fpnames = [a[0][0].id for a in outcomes if a[1] == 4]

    print("True positive: " + str(tp))
    print("False negative: " + str(fn))
    print("True negative: " + str(tn))
    print("False positive: " + str(fp))
    print("True Report: " + str(tr))
    print("False Report: " + str(fr))

    pprint(fpnames)

  @staticmethod
  def outcome(a, tm, tr, e): # activation, threshold, expected value
    true_positive = 1
    false_negative = 2
    true_negative = 3
    false_positive = 4
    true_report = 5
    false_report = 6

    if a > tm and e:
      return true_positive
    if a > tm and not e:
      return false_positive
    if a > tr and e:
      return true_report
    if a > tr and not e:
      return false_report
    if a <= tr and e:
      return false_negative
    return true_negative

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

    confidentCheats = [ConfidentGameAnalysisPivot.fromGamesAnalysisandPrediction(gameAnalysis, PlayerGameActivations.avgAnalysedGameActivation(prediction), engine=True) for gameAnalysis, prediction in zip(cheatGameAnalyses, cheatGamePredictions)]
    confidentLegits = [ConfidentGameAnalysisPivot.fromGamesAnalysisandPrediction(gameAnalysis, PlayerGameActivations.avgAnalysedGameActivation(prediction), engine=False) for gameAnalysis, prediction in zip(legitGameAnalyses, legitGamePredictions)]

    print("writing to db")
    self.env.confidentGameAnalysisPivotDB.lazyWriteMany(confidentCheats + confidentLegits)

  def buildVocabularly(self):
    return self.playerModel.buildVocabularly()

  def buildPlayerGameActivationsTable(self):
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
      predictions = self.predict(gs.quickGameAnalysisTensors())
      pga = PlayerGameActivations.fromTensor(player.id, player.engine, predictions)
      self.env.playerGameActivationsDB.write(pga)

  def predict(self, tensors, generalOnly=False):
    pvs =         [[m[0] for m in p] for p in tensors]
    moveStats =   [[m[1] for m in p] for p in tensors]
    moveNumbers = [[m[2] for m in p] for p in tensors]
    ranks =       [[m[3] for m in p] for p in tensors]
    advs =        [[m[4] for m in p] for p in tensors]
    ambs =        [[m[5] for m in p] for p in tensors]

    predictions = []
    if not generalOnly:
      for p, m, mn, r, a, am in zip(pvs, moveStats, moveNumbers, ranks, advs, ambs):
        predictions.append((
          self.generalGameModel.model().predict(                        [np.array([p]), np.array([m]), np.array([mn]), np.array([r]), np.array([a]), np.array([am])]),
          self.narrowGameModel.model().predict(                         [np.array([p]), np.array([m]), np.array([mn]), np.array([r]), np.array([a]), np.array([am])]),
          self.generalGameModel.intermediateModel().predict([np.array([p]), np.array([m]), np.array([mn]), np.array([r]), np.array([a]), np.array([am])]),
          self.narrowGameModel.intermediateModel().predict(  [np.array([p]), np.array([m]), np.array([mn]), np.array([r]), np.array([a]), np.array([am])])
        ))
    else:
      for p, m, mn, r, a, am in zip(pvs, moveStats, moveNumbers, ranks, advs, ambs):
        predictions.append((
          self.generalGameModel.model().predict([np.array([p]), np.array([m]), np.array([mn]), np.array([r]), np.array([a]), np.array([am])]),
          [],
          [],
          []
        ))
    return predictions

  def report(self, userId, gameAnalysisStore):
    predictions = self.predict(gameAnalysisStore.quickGameAnalysisTensors())
    pga = PlayerGameActivations.fromTensor(userId, None, predictions)
    report = {
      'userId': userId,
      'activation': self.activation(pga, gameAnalysisStore.playerTensor()),
      'games': [Irwin.gameReport(ga, p) for ga, p in zip(gameAnalysisStore.gameAnalyses, predictions)]
    }
    return report

  def predictGames(self, gameTensors):
    # game tensors is a list of tuples in the form: [(gameId, tensor), ...]
    if len(gameTensors) == 0:
      return None
    gameIds = [gid for gid, t in gameTensors]
    predictions = [int(100*np.asscalar(p)) for p in self.gameModel.model().predict([t for gid, t in gameTensors])]
    return list(zip(gameIds, predictions))

  def activation(self, pga, playerTensor): # determined using the player model
    p = self.playerModel.predict(
      pga,
      playerTensor)

    avgPredictions = pga.avgGameActivations
    avgPredictions.sort(reverse=True)

    maxAvg = np.average(avgPredictions[0:2])
    maxAvg = 0 if np.isnan(maxAvg) else int(maxAvg)

    p = min(max(90, maxAvg), p) # if the average activation of the top two games is less than 90, the highest overall activation is 90

    p = p if p > 90 else min(avgPredictions, 90) # if the player model prediction is less than 90, use the average game activation up until 90. Otherwise use the player activation.

    if len(pga.generalActivations) < 7:
      return min(p, 90)
    return p

  @staticmethod
  def gameReport(gameAnalysis, prediction):
    return {
      'gameId': gameAnalysis.gameId,
      'activation': PlayerGameActivations.avgAnalysedGameActivation(prediction),
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

  def discover(self):
    # discover potential cheaters in the database of un-marked players
    print("getting players")
    players = self.env.playerDB.byEngine(None)
    sus = []
    for player in players:
      print("investigating "+player.id)
      gameAnalysisStore = GameAnalysisStore([], [ga for ga in self.env.gameAnalysisDB.byUserId(player.id)])
      predictions = self.predict(gameAnalysisStore.quickGameAnalysisTensors())
      pga = PlayerGameActivations.fromTensor(player.id, None, predictions)
      activation = self.activation(pga, gameAnalysisStore.playerTensor())
      print(str(activation))
      if activation > 70:
        sus.append((player.id, activation))
    pprint(sus)