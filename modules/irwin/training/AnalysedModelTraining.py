from default_imports import *

from modules.game.AnalysedGame import AnalysedGameTensor

from modules.irwin.AnalysedGameModel import AnalysedGameModel

from modules.irwin.Env import Env
from modules.irwin.training.AnalysedGameActivation import AnalysedGameActivation

import numpy as np

from random import shuffle

from pprint import pprint

Batch = NamedTuple('Batch', [
        ('data', np.ndarray),
        ('labels', List[np.ndarray])
    ])

class AnalysedModelTraining(NamedTuple('AnalysedModelTraining', [
        ('env', Env),
        ('analysedGameModel', AnalysedGameModel)
    ])):
    def train(self, epochs: int, filtered: bool = True) -> None:
        logging.debug("getting dataset")
        batch = self.getTrainingDataset(filtered)

        logging.debug("training")
        logging.debug("Batch Info: Games: {}".format(len(batch.data)))

        logging.debug("Game Len: {}".format(len(batch.data[0])))

        self.analysedGameModel.model.fit(
            batch.data, batch.labels,
            epochs=epochs, batch_size=32, validation_split=0.2)

        self.analysedGameModel.saveModel()
        logging.debug("complete")

    def getTrainingDataset(self, filtered: bool):
        if filtered:
            logging.debug("gettings game IDs from DB")
            cheatPivotEntries = self.env.analysedGameActivationDB.byEngineAndPrediction(True, 80)
            legits = self.env.playerDB.byEngine(False)

            shuffle(cheatPivotEntries)
            shuffle(legits)

            legits = legits[:self.env.config["irwin model analysed training sample_size"]]

            logging.debug("Getting game analyses from DB")

            legitAnalysedGames = []

            cheatAnalysedGames = self.env.analysedGameDB.byIds([cpe.id for cpe in cheatPivotEntries])
            [legitAnalysedGames.extend(ga) for ga in self.env.analysedGameDB.byPlayerIds([u.id for u in legits])]
        else:
            logging.debug("getting players by engine")
            cheats = self.env.playerDB.byEngine(True)
            legits = self.env.playerDB.byEngine(False)

            shuffle(cheats)
            shuffle(legits)

            cheats = cheats[:self.env.config["irwin model analysed training sample_size"]]
            legits = legits[:self.env.config["irwin model analysed training sample_size"]]

            cheatAnalysedGames = []
            legitAnalysedGames = []

            logging.debug("getting game analyses from DB")
            [cheatAnalysedGames.extend(ga) for ga in self.env.analysedGameDB.byPlayerIds([u.id for u in cheats])]
            [legitAnalysedGames.extend(ga) for ga in self.env.analysedGameDB.byPlayerIds([u.id for u in legits])]

        logging.debug("building tensor")
        cheatGameTensors = [tga.tensor() for tga in cheatAnalysedGames if tga.gameLength() <= 60]
        legitGameTensors = [tga.tensor() for tga in legitAnalysedGames if tga.gameLength() <= 60]

        logging.debug("batching tensors")
        return self.createBatchAndLabels(cheatGameTensors, legitGameTensors)

    @staticmethod
    def createBatchAndLabels(cheatTensors: List[AnalysedGameTensor], legitTensors: List[AnalysedGameTensor]) -> Batch:
        """
        group the dataset into batches by the length of the dataset, because numpy needs it that way
        """
        mlen = min(len(cheatTensors), len(legitTensors))

        cheats = cheatTensors[:mlen]
        legits = legitTensors[:mlen]

        logging.debug("batch size " + str(len(cheats + legits)))

        labels = [1.0]*len(cheats) + [0.0]*len(legits)

        blz = list(zip(cheats+legits, labels))
        shuffle(blz)

        return Batch(
            data=np.array([t for t, l in blz]),
            labels=[
                np.array([l for t, l in blz]), 
                np.array([[[l]]*(len(t)-13) for t, l in blz]),
                np.array([[[l]]*(len(t)-4) for t, l in blz])
            ])

    def buildTable(self):
        """Build table of activations for analysed games. used for training"""
        logging.warning("Building Analysed Activation Table")
        logging.debug("getting players")
        cheats = self.env.playerDB.byEngine(True)

        lenPlayers = str(len(cheats))

        logging.info("gettings games and predicting")

        for i, p in enumerate(cheats):
            logging.info("predicting: " + p.id + "  -  " + str(i) + '/' + lenPlayers)
            analysedGames = self.env.analysedGameDB.byPlayerId(p.id)
            predictions = self.analysedGameModel.predict(analysedGames)
            analysedGameActivations = [AnalysedGameActivation.fromAnalysedGameAndPrediction(
                analysedGame = analysedGame,
                prediction = prediction,
                engine=p.engine) for analysedGame, prediction in zip(analysedGames, predictions)]
            self.env.analysedGameActivationDB.lazyWriteMany(analysedGameActivations)