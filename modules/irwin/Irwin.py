from pprint import pprint
from random import shuffle
from math import ceil
from functools import lru_cache

import logging
import numpy as np
import os.path

from modules.irwin.AnalysedGameModel import AnalysedGameModel
from modules.irwin.BasicGameModel import BasicGameModel

from modules.irwin.GameAnalysisActivation import GameAnalysisActivation

from modules.irwin.Evaluation import Evaluation

from modules.core.GameAnalysisStore import GameAnalysisStore

class Irwin(Evaluation):
    def __init__(self, env):
        self.env = env
        self.basicGameModel = BasicGameModel(env)
        self.analysedGameModel = AnalysedGameModel(env)

    def predictAnalysed(self, tensors):
        return [self.analysedGameModel.model().predict(np.array([t])) for t in tensors]

    def predictBasicGames(self, gameTensors):
        # game tensors is a list of tuples in the form: [(gameId, tensor), ...]
        if len(gameTensors) == 0:
            return None
        gameIds = [gid for gid, t in gameTensors]
        predictions = [int(100*np.asscalar(p)) for p in self.basicGameModel.model().predict(np.array([t for gid, t in gameTensors]))]
        return list(zip(gameIds, predictions))

    def activation(self, predictions, gamesMoveActivations=None):
        if gamesMoveActivations is None:
            gamesMoveActivations = [[int(50*(p[0][0] + p[1][0])) for p in zip(list(prediction[1][0]), list(prediction[2][0]))] for prediction in predictions]
        gamesPOverX = [Irwin.pOverX(moveActivations, 90) for moveActivations in gamesMoveActivations]
        gameOverallPredictions = [100*p[0][0] for p in predictions]
        sortedGameActivations = sorted([int(0.5*(a+o)) for a, o in zip(gamesPOverX, gameOverallPredictions)], reverse=True)

        top30games = sortedGameActivations[:ceil(0.3*len(sortedGameActivations))]
        top30avgGames = int(np.average(top30games)) if len(top30games) > 0 else 0

        above90 = len([a for a in sortedGameActivations if a > 90])
        above80 = len([a for a in sortedGameActivations if a > 80])

        if len(gamesPOverX) < 6 or above90 < 3:
            result = min(90, top30avgGames) # Not enough games to mark
        elif above80 == 0:
            result = min(60, top30avgGames) # Not enough games to report
        else:
            result = top30avgGames # Normal activation

        return result

    def report(self, userId, gameAnalysisStore):
        predictions = self.predictAnalysed(gameAnalysisStore.gameAnalysisTensors())
        gamesMoveActivations = [[int(50*(p[0][0] + p[1][0])) for p in zip(list(prediction[1][0]), list(prediction[2][0]))] for prediction in predictions]
        report = {
            'userId': userId,
            'activation': self.activation(predictions, gamesMoveActivations),
            'games': [Irwin.gameReport(ga, p, ma) for ga, p, ma in zip(gameAnalysisStore.gameAnalyses, predictions, gamesMoveActivations)]
        }
        return report

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
    def pOverX(moveActivations, x): # percentage of moveActivations > X in the list
        l = len([a for a in moveActivations if a > x])
        if l == 0 or len(moveActivations) == 0:
            return 0
        return int(100*l/len(moveActivations))

    @staticmethod
    def top30avg(moveActivations):
        top30 = sorted(moveActivations, reverse=True)[:ceil(0.3*len(moveActivations))]
        res = int(np.average(top30)) if len(top30) > 0 else 0
        return res

    def discover(self):
        # discover potential cheaters in the database of un-marked players
        logging.warning("Discovering unprocessed players")
        logging.debug("getting players")
        players = self.env.playerDB.byEngine(None)
        sus = []
        for player in players:
            logging.debug("investigating "+player.id)
            gameAnalysisStore = GameAnalysisStore([], [ga for ga in self.env.gameAnalysisDB.byUserId(player.id)])
            predictions = self.predictAnalysed(gameAnalysisStore.gameAnalysisTensors())
            activation = self.activation(predictions)
            logging.debug(str(activation))
            if activation > 90:
                print("SUSPICIOUS")
                sus.append((player.id, activation))
        pprint(sus)

    def buildAnalysedActivationTable(self):
        logging.warning("Building Analysed Activation Table")
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
        cheatGamePredictions = self.predictAnalysed(cheatTensors)
        legitGamePredictions = self.predictAnalysed(legitTensors)

        confidentCheats = [GameAnalysisActivation.fromGamesAnalysisandPrediction(gameAnalysis, int(100*prediction[0][0]), engine=True) for gameAnalysis, prediction in zip(cheatGameAnalyses, cheatGamePredictions)]
        confidentLegits = [GameAnalysisActivation.fromGamesAnalysisandPrediction(gameAnalysis, int(100*prediction[0][0]), engine=False) for gameAnalysis, prediction in zip(legitGameAnalyses, legitGamePredictions)]

        logging.debug("writing to db")
        self.env.gameAnalysisActivationDB.lazyWriteMany(confidentCheats + confidentLegits)

    def buildBasicActivationTable(self):
        logging.warning("Building Basic Activation Table")
        logging.debug("getting games")
        cheats = self.env.playerDB.byEngine(True)
        legits = self.env.playerDB.byEngine(False)

        cheatTensorsByIdAndUser = []
        legitTensorsByIdAndUser = []

        for p in cheats + legits:
            tensorsByIdAndUser = [(g.id, p.id, g.tensor(p.id)) for g in self.env.gameDB.byUserId(p.id)]
            if p.engine:
                cheatTensorsByIdAndUser.extend(tensorsByIdAndUser)
            else:
                legitTensorsByIdAndUser.extend(tensorsByIdAndUser)

        cheatGamePredictions = self.predictBasicGames([(g[0], g[2]) for g in cheatTensorsByIdAndUser])
        legitGamePredictions = self.predictBasicGames([(g[0], g[2]) for g in legitTensorsByIdAndUser])

        cheatPredictionsByIdAndUser = [(p[0], t[1], p[1]) for p, t in zip(cheatGamePredictions, cheatTensorsByIdAndUser)] # [(gameId, userId, prediction)]
        legitPredictionsByIdAndUser = [(p[0], t[1], p[1]) for p, t in zip(legitGamePredictions, legitTensorsByIdAndUser)] # [(gameId, userId, prediction)]