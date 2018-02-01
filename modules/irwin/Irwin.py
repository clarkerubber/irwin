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
        return [(self.analysedGameModel.model().predict(np.array([t])), length) for t, length in tensors]

    def predictBasicGames(self, gameTensors):
        # game tensors is a list of tuples in the form: [(gameId, tensor), ...]
        if len(gameTensors) == 0:
            return None
        gameIds = [gid for gid, t in gameTensors]
        predictions = [int(100*np.asscalar(p)) for p in self.basicGameModel.model().predict(np.array([t for gid, t in gameTensors]))]
        return list(zip(gameIds, predictions))

    @staticmethod
    def activation(gameActivations):
        sortedGameActivations = sorted(gameActivations, reverse=True)
        topXgames = sortedGameActivations[:ceil(0.1*len(sortedGameActivations))]
        topXgamesAvg = int(np.average(topXgames)) if len(topXgames) > 0 else 0

        aboveUpper = len([a for a in sortedGameActivations if a > 90])
        aboveLower = len([a for a in sortedGameActivations if a > 70])

        if aboveUpper > 2:
            result = topXgamesAvg # enough games to mark
        elif aboveLower > 0:
            result = min(90, topXgamesAvg) # Not enough games to mark
        else:
            result = min(60, topXgamesAvg) # Not enough games to report

        return result

    @staticmethod
    def gameActivation(gamePredictions, gameLength):
        moveActivations = [Irwin.moveActivation(movePrediction) for movePrediction in Irwin.movePredictions(gamePredictions)][:gameLength]
        gameOverall = 100*gamePredictions[0][0]
        pOverX = Irwin.pOverX(moveActivations, 80)
        top30avg = np.average(sorted(moveActivations, reverse=True)[:ceil(0.3*len(moveActivations))])
        return int(np.average([gameOverall, pOverX, top30avg]))

    @staticmethod
    def movePredictions(gamePredictions):
        return list(zip(list(gamePredictions[1][0]), list(gamePredictions[2][0])))

    @staticmethod
    def moveActivation(movePrediction):
        return int(50*(movePrediction[0][0]+movePrediction[1][0]))

    def report(self, userId, gameAnalysisStore):
        playerPredictions = self.predictAnalysed(gameAnalysisStore.gameAnalysisTensors())
        gameActivations = [Irwin.gameActivation(gamePredictions, gameLength) for gamePredictions, gameLength in playerPredictions]
        report = {
            'userId': userId,
            'activation': self.activation(gameActivations),
            'games': [Irwin.gameReport(ga, a, gp) for ga, a, gp in zip(gameAnalysisStore.gameAnalyses, gameActivations, playerPredictions)]
        }
        return report

    @staticmethod
    def gameReport(gameAnalysis, gameActivation, gamePredictions):
        return {
            'gameId': gameAnalysis.gameId,
            'activation': gameActivation,
            'moves': [Irwin.moveReport(am, p) for am, p in zip(gameAnalysis.moveAnalyses, Irwin.movePredictions(gamePredictions[0]))]
        }

    @staticmethod
    def moveReport(analysedMove, movePrediction):
        return {
            'a': Irwin.moveActivation(movePrediction),
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