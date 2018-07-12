from default_imports import *

from modules.game.Game import GameTensor

from modules.irwin.BasicGameModel import BasicGameModel

from modules.irwin.Env import Env
from modules.irwin.training.BasicGameActivation import BasicGameActivation

import numpy as np

from random import shuffle

Batch = NamedTuple('Batch', [
        ('data', np.ndarray),
        ('labels', np.ndarray)
    ])

class BasicModelTraining(NamedTuple('BasicModelTraining', [
        ('env', Env),
        ('basicGameModel', BasicGameModel)
    ])):
    def train(self, epochs: int, filtered: bool = True, newmodel: bool = False):
        logging.debug("getting dataset")
        batch = self.getTrainingDataset(filtered)

        logging.debug("training")
        logging.debug("Batch Info: Games: {}".format(len(batch.data)))

        self.basicGameModel.model.fit(
            batch.data, batch.labels,
            epochs=epochs, batch_size=32, validation_split=0.2)

        self.basicGameModel.saveModel()
        logging.debug("complete")

    def getTrainingDataset(self, filtered: bool):
        logging.debug("Getting players from DB")

        cheatTensors = []
        legitTensors = []

        logging.debug("Getting games from DB")
        if filtered:
            legits = self.env.playerDB.byEngine(False)
            shuffle(legits)
            legits = legits[:self.Env.config["irwin model basic training sample_size"]]
            for p in legits:
                legitTensors.extend([g.tensor(p.id) for g in self.env.gameDB.byPlayerIdAndAnalysed(p.id)])
            cheatGameActivations = self.env.basicGameActivationDB.byEngineAndPrediction(True, 70)
            cheatGames = self.env.gameDB.byIds([ga.gameId for ga in cheatGameActivations])
            cheatTensors.extend([g.tensor(ga.userId) for g, ga in zip(cheatGames, cheatGameActivations)])

        else:
            cheats = self.env.playerDB.byEngine(True)
            legits = self.env.playerDB.byEngine(False)

            shuffle(cheats)
            shuffle(legits)

            cheats = cheats[:self.Env.config["irwin model basic training sample_size"]]
            legits = legits[:self.Env.config["irwin model basic training sample_size"]]

            for p in legits + cheats:
                if p.engine:
                    cheatTensors.extend([g.tensor(p.id) for g in self.env.gameDB.byPlayerIdAndAnalysed(p.id)])
                else:
                    legitTensors.extend([g.tensor(p.id) for g in self.env.gameDB.byPlayerIdAndAnalysed(p.id)])

        cheatTensors = [t for t in cheatTensors if t is not None]
        legitTensors = [t for t in legitTensors if t is not None]

        shuffle(cheatTensors)
        shuffle(legitTensors)

        logging.debug("batching tensors")
        return self.createBatchAndLabels(cheatTensors, legitTensors)

    @staticmethod
    def createBatchAndLabels(cheatTensors: List[GameTensor], legitTensors: List[GameTensor]) -> Batch:
        """
        group the dataset into batches by the length of the dataset, because numpy needs it that way
        """
        mlen = min(len(cheatTensors), len(legitTensors))

        cheats = cheatTensors[:mlen]
        legits = legitTensors[:mlen]

        logging.debug("batch size " + str(len(cheats + legits)))

        labels = [1]*len(cheats) + [0]*len(legits)

        blz = list(zip(cheats+legits, labels))
        shuffle(blz)

        return Batch(
            data = np.array([t for t, l in blz]),
            labels = np.array([l for t, l in blz])
        )

    def buildTable(self):
        """
        Build table of activations for basic games (analysed by lichess). used for training
        """
        logging.debug("Building Basic Activation Table")
        logging.info("getting players")
        cheats = self.env.playerDB.byEngine(True)

        lenPlayers = str(len(cheats))

        logging.info("getting games and predicting")
        for i, p in enumerate(cheats):
            logging.info("predicting: " + p.id + "  -  " + str(i) + "/" + lenPlayers)

            games = self.env.gameDB.byPlayerIdAndAnalysed(p.id)
            gamesAndTensors = zip(games,self.basicGameModel.predict(p.id, games))

            self.env.basicGameActivationDB.lazyWriteMany([BasicGameActivation.fromPrediction(
                gameId=g.id,
                playerId=p.id,
                prediction=pr,
                engine=p.engine) for g, pr in gamesAndTensors if pr is not None])