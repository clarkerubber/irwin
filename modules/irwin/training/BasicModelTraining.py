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
    def train(self, epochs: int, filtered: bool = False, newmodel: bool = False):
        logging.debug("getting dataset")
        batch = self.getTrainingDataset(filtered)

        logging.debug("training")
        logging.debug("Batch Info: Games: {}".format(len(batch.data[0])))

        self.basicGameModel.model.fit(
            batch.data, batch.labels,
            epochs=epochs, batch_size=32, validation_split=0.2)

        self.basicGameModel.saveModel()
        logging.debug("complete")

    def getPlayerTensors(self, playerId: str):
        games = self.env.gameDB.byPlayerIdAndAnalysed(playerId)
        return list(filter(None, [g.tensor(playerId) for g in games]))

    def getTensorsByEngine(self, engine: bool, limit: int):
        players = self.env.playerDB.byEngine(engine)
        shuffle(players)

        tensors = []

        for player in players:
            logging.info(f'getting tensors for {player.id}')

            tensors.extend(self.getPlayerTensors(player.id))
            l = len(tensors)

            logging.info(f'loaded {l} / {limit} tensors')

            if l >= limit:
                logging.info('reached limit')
                break

        return tensors

    def getTensorByCPE(self, cpe):
        game = self.env.gameDB.byId(cpe.gameId)
        return game.tensor(cpe.playerId)


    def getFilteredEngineTensors(self, limit: int):
        logging.info(f'getting {limit} filtered tensors')

        cheatPivotEntries = self.env.basicGameActivationDB.byEngineAndPrediction(
            engine = True,
            prediction = 70,
            limit = limit)

        return list(filter(None, [self.getTensorByCPE(cpe) for cpe in cheatPivotEntries]))

    def getTrainingDataset(self, filtered: bool = False):
        logging.debug("Getting players from DB")

        limit = self.env.config['irwin model basic training sample_size']

        legitTensors = self.getTensorsByEngine(
            engine = False,
            limit = limit)

        if filtered:
            cheatTensors = self.getFilteredEngineTensors(limit = limit)
        else:
            cheatTensors = self.getTensorsByEngine(
                engine = True,
                limit = limit)

        logging.debug("batching tensors")
        return self.createBatchAndLabels(cheatTensors, legitTensors)

    @staticmethod
    def createBatchAndLabels(cheatTensors: List[GameTensor], legitTensors: List[GameTensor]) -> Batch:
        """
        group the dataset into batches by the length of the dataset, because numpy needs it that way
        """
        logging.debug(len(cheatTensors))
        logging.debug(len(legitTensors))
        mlen = min(len(cheatTensors), len(legitTensors))
        logging.debug(mlen)

        cheats = cheatTensors[:mlen]
        legits = legitTensors[:mlen]

        logging.debug("batch size " + str(len(cheats + legits)))

        labels = [1]*len(cheats) + [0]*len(legits)

        blz = list(zip(cheats+legits, labels))
        shuffle(blz)

        b = Batch(
            data = [
                np.array([t[0] for t, l in blz]),
                np.array([t[1] for t, l in blz])
            ],
            labels = np.array([l for t, l in blz])
        )

        return b

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
            gamesAndTensors = zip(games, self.basicGameModel.predict(p.id, games))

            self.env.basicGameActivationDB.writeMany([BasicGameActivation.fromPrediction(
                gameId=g.id,
                playerId=p.id,
                prediction=pr,
                engine=p.engine) for g, pr in gamesAndTensors if pr is not None])