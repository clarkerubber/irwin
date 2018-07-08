from default_imports import *

from modules.irwin.training.Env import Env
from modules.game.AnalysedGame import AnalysedGameTensor
from modules.irwin.AnalysedGameModel import AnalysedGameModel

from numpy import ndarray

from random import shuffe

Batch = NamedTuple('Batch', [
        ('data', ndarray),
        ('labels', List[ndarray])
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

            legits = legits[:10000]

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

            cheats = cheats[:10000]
            legits = legits[:10000]

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
        # group the dataset into batches by the length of the dataset, because numpy needs it that way
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