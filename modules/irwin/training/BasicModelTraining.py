from default_imports import *

from modules.game.Game import GameTensor

from modules.irwin.training.Env import Env
from modules.irwin.BasicGameModel import BasicGameModel

from numpy import ndarray

from random import shuffle

Batch = NamedTuple('Batch', [
        ('data', ndarray),
        ('labels', ndarray)
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
            legits = legits[:10000]
            for p in legits:
                legitTensors.extend([g.tensor(p.id) for g in self.env.gameDB.byPlayerIdAnalysed(p.id)])
            cheatGameActivations = self.env.gameBasicActivationDB.byEngineAndPrediction(True, 70)
            cheatGames = self.env.gameDB.byIds([ga.gameId for ga in cheatGameActivations])
            cheatTensors.extend([g.tensor(ga.userId) for g, ga in zip(cheatGames, cheatGameActivations)])

        else:
            cheats = self.env.playerDB.byEngine(True)
            legits = self.env.playerDB.byEngine(False)

            shuffle(cheats)
            shuffle(legits)

            cheats = cheats[:10000]
            legits = legits[:10000]

            for p in legits + cheats:
                if p.engine:
                    cheatTensors.extend([g.tensor(p.id) for g in self.env.gameDB.byPlayerIdAnalysed(p.id)])
                else:
                    legitTensors.extend([g.tensor(p.id) for g in self.env.gameDB.byPlayerIdAnalysed(p.id)])

        cheatTensors = [t for t in cheatTensors if t is not None]
        legitTensors = [t for t in legitTensors if t is not None]

        shuffle(cheatTensors)
        shuffle(legitTensors)

        logging.debug("batching tensors")
        return self.createBatchAndLabels(cheatTensors, legitTensors)

    @staticmethod
    def createBatchAndLabels(cheatTensors: List[GameTensor], legitTensors: List[GameTensor]) -> Batch:
        # group the dataset into batches by the length of the dataset, because numpy needs it that way
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