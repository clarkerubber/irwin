from default_imports import *

from modules.game.AnalysedGame import AnalysedGameTensor, GameAnalysedGame

from modules.irwin.AnalysedGameModel import AnalysedGameModel

from modules.irwin.Env import Env
from modules.irwin.training.AnalysedGameActivation import AnalysedGameActivation

import numpy as np

from random import shuffle

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
        logging.debug("Batch Info: Games: {}".format(len(batch.data[0])))

        logging.debug("Game Len: {}".format(len(batch.data[0][0])))

        self.analysedGameModel.model.fit(
            batch.data, batch.labels,
            epochs=epochs, batch_size=32, validation_split=0.2)

        self.analysedGameModel.saveModel()
        logging.debug("complete")

    def getTrainingDataset(self, filtered: bool):
        cheatAnalysedGames = []
        legitAnalysedGames = []

        if filtered:
            logging.debug("gettings game IDs from DB")
            cheatPivotEntries = self.env.analysedGameActivationDB.byEngineAndPrediction(True, 80)
            legits = self.env.playerDB.byEngine(False)

            logging.debug('cpes: ' + str(len(cheatPivotEntries)))
            logging.debug('legits: ' + str(len(legits)))

            shuffle(cheatPivotEntries)
            shuffle(legits)

            #cheatPivotEntries = cheatPivotEntries[:self.env.config["irwin model analysed training sample_size"]]
            legits = legits[:self.env.config["irwin model analysed training sample_size"]]

            logging.debug('legits: ' + str(len(legits)))

            logging.debug("Getting game analyses from DB")

            [legitAnalysedGames.extend(ga) for ga in self.env.analysedGameDB.byPlayerIds([u.id for u in legits])]
            cheatAnalysedGames = self.env.analysedGameDB.byIds([cpe.id for cpe in cheatPivotEntries][:len(legitAnalysedGames)])

            logging.debug('cags: ' + str(len(cheatAnalysedGames)))
            logging.debug('lags: ' + str(len(legitAnalysedGames)))
        else:
            logging.debug("getting players by engine")
            cheats = self.env.playerDB.byEngine(True)
            legits = self.env.playerDB.byEngine(False)

            logging.debug('cheats: ' + str(len(cheats)))
            logging.debug('legits: ' + str(len(legits)))

            shuffle(cheats)
            shuffle(legits)

            cheats = cheats[:self.env.config["irwin model analysed training sample_size"]]
            legits = legits[:self.env.config["irwin model analysed training sample_size"]]

            logging.debug('cheats: ' + str(len(cheats)))
            logging.debug('legits: ' + str(len(legits)))

            logging.debug("getting game analyses from DB")
            [cheatAnalysedGames.extend(ga) for ga in self.env.analysedGameDB.byPlayerIds([u.id for u in cheats])]
            [legitAnalysedGames.extend(ga) for ga in self.env.analysedGameDB.byPlayerIds([u.id for u in legits])]

            logging.debug('cags: ' + str(len(cheatAnalysedGames)))
            logging.debug('lags: ' + str(len(legitAnalysedGames)))

        logging.debug('getting games from DB')
        cheatGames = self.env.gameDB.byIds([ag.gameId for ag in cheatAnalysedGames])
        legitGames = self.env.gameDB.byIds([ag.gameId for ag in legitAnalysedGames])

        logging.debug('cgs: ' + str(len(cheatGames)))
        logging.debug('lgs: ' + str(len(legitGames)))

        logging.debug("building tensor")
        cheatGameTensors = list(filter(None, [GameAnalysedGame(ag, g).tensor() for ag, g in zip(cheatAnalysedGames, cheatGames) if ag.gameLength() <= 60]))
        legitGameTensors = list(filter(None, [GameAnalysedGame(ag, g).tensor() for ag, g in zip(legitAnalysedGames, legitGames) if ag.gameLength() <= 60]))

        logging.debug('cgts: ' + str(len(cheatGameTensors)))
        logging.debug('lgts: ' + str(len(legitGameTensors)))

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

        r =  Batch(
            data = [
                np.array([t[0] for t, l in blz]),
                np.array([t[1] for t, l in blz])
            ],
            labels=[
                np.array([l for t, l in blz]), 
                np.array([ [[l]]*(60-13) for t, l in blz]),
                np.array([ [[l]]*(60-4) for t, l in blz])
            ])
        logging.debug(r.labels[0])
        logging.debug(r.labels[1])
        logging.debug(r.labels[2])
        return r

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
            games = self.env.gameDB.byIds([ag.gameId for ag in analysedGames])

            predictions = self.analysedGameModel.predict([GameAnalysedGame(ag, g) for ag, g in zip(analysedGames, games)])

            analysedGameActivations = [AnalysedGameActivation.fromAnalysedGameAndPrediction(
                analysedGame = analysedGame,
                prediction = prediction,
                engine=p.engine) for analysedGame, prediction in zip(analysedGames, predictions) if prediction is not None]
            self.env.analysedGameActivationDB.writeMany(analysedGameActivations)