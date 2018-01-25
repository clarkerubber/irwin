from pprint import pprint
from random import shuffle
from math import ceil
from functools import lru_cache

import logging
import numpy as np
import os.path

from modules.irwin.AnalysedGameModel import AnalysedGameModel
from modules.irwin.GameModel import GameModel

from modules.irwin.ConfidentGameAnalysisPivot import ConfidentGameAnalysisPivot, ConfidentGameAnalysisPivotDB

from modules.core.GameAnalysisStore import GameAnalysisStore

class Irwin():
  def __init__(self, env, config):
    self.env = env
    self.config = config
    self.gameModel = GameModel(env)
    self.generalGameModel = AnalysedGameModel(env, 'general')
    self.narrowGameModel = AnalysedGameModel(env, 'narrow')

  def getEvaluationDataset(self, batchSize):
    print("getting players", end="...", flush=True)
    players = self.env.playerDB.balancedSample(batchSize)
    print(" %d" % len(players))
    print("getting game analyses")
    analysesByPlayer = [(player, GameAnalysisStore([], [ga for ga in self.env.gameAnalysisDB.byUserId(player.id)])) for player in players]
    return analysesByPlayer

  def evaluate(self):
    logging.warning("Evaluating Model")
    logging.debug("Getting Dataset")
    analysisStoreByPlayer = self.getEvaluationDataset(self.config['evalSize'])
    activations = [self.activation(self.predict(gameAnalysisStore.quickGameAnalysisTensors())) for player, gameAnalysisStore in analysisStoreByPlayer]
    outcomes = list([(ap, Irwin.outcome(a, 90, 60, ap[0].engine)) for ap, a in zip(analysisStoreByPlayer, activations)])
    tp = len([a for a in outcomes if a[1] == 1])
    fn = len([a for a in outcomes if a[1] == 2])
    tn = len([a for a in outcomes if a[1] == 3])
    fp = len([a for a in outcomes if a[1] == 4])
    tr = len([a for a in outcomes if a[1] == 5])
    fr = len([a for a in outcomes if a[1] == 6])

    fpnames = [a[0][0].id for a in outcomes if a[1] == 4]

    logging.warning("True positive: " + str(tp))
    logging.warning("False negative: " + str(fn))
    logging.warning("True negative: " + str(tn))
    logging.warning("False positive: " + str(fp))
    logging.warning("True Report: " + str(tr))
    logging.warning("False Report: " + str(fr))

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

  def buildConfidenceTable(self):
    logging.warning("Building Confidence Table")
    logging.debug("getting games")
    cheats = self.env.playerDB.byEngine(True)
    legits = self.env.playerDB.byEngine(False)

    cheatGameAnalyses = []
    [cheatGameAnalyses.extend(ga) for ga in self.env.gameAnalysisDB.byUserIds([u.id for u in cheats])]
    legitGameAnalyses = []
    [legitGameAnalyses.extend(ga) for ga in self.env.gameAnalysisDB.byUserIds([u.id for u in legits])]

    logging.debug("getting moveAnalysisTensors")
    cheatTensors = [tga.moveAnalysisTensors() for tga in cheatGameAnalyses]
    legitTensors = [tga.moveAnalysisTensors() for tga in legitGameAnalyses]

    logging.debug("predicting the things")
    cheatGamePredictions = self.predict(cheatTensors, general=False)
    legitGamePredictions = self.predict(legitTensors, general=False)

    confidentCheats = [ConfidentGameAnalysisPivot.fromGamesAnalysisandPrediction(gameAnalysis, int(100*prediction[0][0]), engine=True) for gameAnalysis, prediction in zip(cheatGameAnalyses, cheatGamePredictions)]
    confidentLegits = [ConfidentGameAnalysisPivot.fromGamesAnalysisandPrediction(gameAnalysis, int(100*prediction[0][0]), engine=False) for gameAnalysis, prediction in zip(legitGameAnalyses, legitGamePredictions)]

    logging.debug("writing to db")
    self.env.confidentGameAnalysisPivotDB.lazyWriteMany(confidentCheats + confidentLegits)

  def predict(self, tensors, general=False):
    if general:
      predictions = [self.generalGameModel.model().predict(np.array([t])) for t in tensors]   
    else:
      predictions = [self.narrowGameModel.model().predict(np.array([t])) for t in tensors]
    return predictions

  def predictGames(self, gameTensors):
    # game tensors is a list of tuples in the form: [(gameId, tensor), ...]
    if len(gameTensors) == 0:
      return None
    gameIds = [gid for gid, t in gameTensors]
    predictions = [int(100*np.asscalar(p)) for p in self.gameModel.model().predict(np.array([t for gid, t in gameTensors]))]
    return list(zip(gameIds, predictions))

  @staticmethod
  def top30avg(moveActivations):
    top30 = sorted(moveActivations, reverse=True)[:ceil(0.3*len(moveActivations))]
    res = int(np.average(top30)) if len(top30) > 0 else 0
    return res

  def report(self, userId, gameAnalysisStore):
    predictions = self.predict(gameAnalysisStore.quickGameAnalysisTensors())
    gamesMoveActivations = [[int(50*(p[0][0] + p[1][0])) for p in zip(list(prediction[1][0]), list(prediction[2][0]))] for prediction in predictions]
    report = {
      'userId': userId,
      'activation': self.activation(predictions, gamesMoveActivations),
      'games': [Irwin.gameReport(ga, p, ma) for ga, p, ma in zip(gameAnalysisStore.gameAnalyses, predictions, gamesMoveActivations)]
    }
    return report

  def activation(self, predictions, gamesMoveActivations=None):
    if gamesMoveActivations is None:
      gamesMoveActivations = [[int(50*(p[0][0] + p[1][0])) for p in zip(list(prediction[1][0]), list(prediction[2][0]))] for prediction in predictions]
    gamesTop30avg = [Irwin.top30avg(moveActivations) for moveActivations in gamesMoveActivations]
    gameOverallPredictions = [100*p[0][0] for p in predictions]
    gameActivations = [int(0.5*(a+o)) for a, o in zip(gamesTop30avg, gameOverallPredictions)]
    top30games = sorted(gameActivations, reverse=True)[:ceil(0.3*len(gameActivations))]
    top30avgGames = int(np.average(top30games)) if len(top30games) > 0 else 0
    return min(90, top30avgGames) if len(gamesTop30avg) < 6 else top30avgGames

  @staticmethod
  def gameReport(gameAnalysis, prediction, moveActivations):
    return {
      'gameId': gameAnalysis.gameId,
      'activation': int(50*prediction[0][0] + 0.5*Irwin.top30avg(moveActivations)),
      'moves': [Irwin.moveReport(am, p) for am, p in zip(gameAnalysis.moveAnalyses, moveActivations)]
    }

  @staticmethod
  def moveReport(analysedMove, prediction):
    return {
      'a': prediction,
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
    logging.warning("Discovering unprocessed players")
    logging.debug("getting players")
    players = self.env.playerDB.byEngine(None)
    sus = []
    for player in players:
      logging.debug("investigating "+player.id)
      gameAnalysisStore = GameAnalysisStore([], [ga for ga in self.env.gameAnalysisDB.byUserId(player.id)])
      predictions = self.predict(gameAnalysisStore.quickGameAnalysisTensors())
      pga = PlayerGameActivations.fromTensor(player.id, None, predictions)
      activation = self.activation(pga, gameAnalysisStore.playerTensor())
      logging.debug(str(activation))
      if activation > 70:
        sus.append((player.id, activation))
    pprint(sus)