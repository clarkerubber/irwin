from default_imports import *

from multiprocessing import Pool

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

    def getPlayerTensors(self, playerId: str):
        analysedGames = self.env.analysedGameDB.byPlayerId(playerId)
        games = self.env.gameDB.byIds([ag.gameId for ag in analysedGames])

        return list(filter(None, [GameAnalysedGame(ag, g).tensor() for ag, g in zip(analysedGames, games) if ag.gameLength() <= 60]))

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
        analysedGame = self.env.analysedGameDB.byId(cpe.id)
        if analysedGame is not None and analysedGame.gameLength() <= 60:
            game = self.env.gameDB.byId(analysedGame.gameId)
            return GameAnalysedGame(analysedGame, game).tensor()
        return None

    def getFilteredEngineTensors(self, limit: int):
        logging.info(f'getting {limit} filtered tensors')

        cheatPivotEntries = self.env.analysedGameActivationDB.byEngineAndPrediction(
            engine = True,
            prediction = 80,
            limit = limit)

        return list(filter(None, [self.getTensorByCPE(cpe) for cpe in cheatPivotEntries]))

    def getTrainingDataset(self, filtered: bool):
        limit = self.env.config["irwin model analysed training sample_size"]

        legitTensors = self.getTensorsByEngine(
            engine = False,
            limit = limit)

        if filtered:
            cheatTensors = self.getFilteredEngineTensors(limit = limit)
        else:
            cheatTensors = self.getTensorsByEngine(
                engine = True,
                limit = limit)

        logging.debug('cgts: ' + str(len(cheatTensors)))
        logging.debug('lgts: ' + str(len(legitTensors)))

        logging.debug("batching tensors")
        return self.createBatchAndLabels(cheatTensors, legitTensors)

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