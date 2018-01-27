import numpy as np
import logging
import os

from random import shuffle

from collections import namedtuple

from keras.models import load_model, Model
from keras.layers import Embedding, Dropout, Dense, Reshape, LSTM, Input, concatenate, Conv1D, Flatten
from keras.optimizers import Adam

from functools import lru_cache

class AnalysedGameModel(namedtuple('AnalysedGameModel', ['env'])):
    @lru_cache(maxsize=2)
    def model(self, newmodel=False):
        if os.path.isfile('modules/irwin/models/analysedGame.h5') and not newmodel:
            logging.debug("model already exists, opening from file")
            return load_model('modules/irwin/models/analysedGame.h5')
        logging.debug('model does not exist, building from scratch')
        inputGame = Input(shape=(60, 10), dtype='float32', name='game_input')

        # Merge embeddings

        ### Conv Net Block of Siamese Network
        conv1 = Conv1D(filters=64, kernel_size=3, activation='relu')(inputGame)
        dense1 = Dense(32, activation='relu')(conv1)
        conv2 = Conv1D(filters=64, kernel_size=5, activation='relu')(dense1)
        dense2 = Dense(32, activation='sigmoid')(conv2)
        conv3 = Conv1D(filters=64, kernel_size=10, activation='relu')(dense2)
        dense3 = Dense(16, activation='relu')(conv3)
        dense4 = Dense(8, activation='sigmoid')(dense3)

        f = Flatten()(dense4)
        dense5 = Dense(64, activation='relu')(f)
        convNetOutput = Dense(16, activation='sigmoid')(dense5)


        ### LSTM Block of Siamese Network
        # merge move stats with move options
        c1 = Conv1D(filters=128, kernel_size=5, name='conv1')(inputGame)

        # analyse all the moves and come to a decision about the game
        l1 = LSTM(128, return_sequences=True)(c1)
        l2 = LSTM(128, return_sequences=True, activation='sigmoid')(l1)

        c2 = Conv1D(filters=64, kernel_size=10, name='conv2')(l2)

        l3 = LSTM(64, return_sequences=True)(c2)
        l4 = LSTM(32, return_sequences=True, activation='sigmoid', name='position_words')(l3)
        l5 = LSTM(32)(l4)
        l6 = Dense(16, activation='sigmoid', name='game_word')(l5)
        d4 = Dropout(0.3)(l6)

        s1 = Dense(16, activation='sigmoid')(l4)
        lstmMove = Dense(1, activation='sigmoid', name='lstm_move_output')(s1)

        # isolated consideration of move blocks

        mi1 = Dense(64, activation='relu')(c1)
        mi2 = Dense(16, activation='relu')(mi1)
        isolatedMove = Dense(1, activation='sigmoid', name='isolated_move')(mi2)


        mergeLSTMandConv = concatenate([d4, convNetOutput])
        denseOut1 = Dense(16, activation='sigmoid')(mergeLSTMandConv)
        mainOutput = Dense(1, activation='sigmoid', name='main_output')(denseOut1)

        model = Model(inputs=inputGame, outputs=[mainOutput, lstmMove, isolatedMove])

        model.compile(optimizer=Adam(lr=0.0001),
            loss='binary_crossentropy',
            loss_weights=[1., 0.3, 0.2],
            metrics=['accuracy'])
        return model

    def train(self, epochs, filtered=True, newmodel=False):
        # get player sample
        logging.debug("getting model")
        model = self.model(newmodel)
        logging.debug("getting dataset")
        batch = self.getTrainingDataset(filtered)

        logging.debug("training")
        logging.debug("Batch Info: Games: " + str(len(batch['data'])))

        logging.debug("Game Len: " + str(len(batch['data'][0])))

        model.fit(batch['data'], batch['labels'], epochs=epochs, batch_size=32, validation_split=0.2)

        self.saveModel(model)
        logging.debug("complete")

    def saveModel(self, model):
        logging.debug("saving model")
        model.save('modules/irwin/models/analysedGame.h5')

    def getTrainingDataset(self, filtered):
        if filtered:
            logging.debug("gettings game IDs from DB")
            cheatPivotEntries = self.env.gameAnalysisActivationDB.byEngineAndPrediction(True, 80)
            legits = self.env.playerDB.byEngine(False)

            shuffle(cheatPivotEntries)
            shuffle(legits)

            logging.debug("Getting game analyses from DB")

            legitGameAnalyses = []

            cheatGameAnalyses = self.env.gameAnalysisDB.byIds([cpe.id for cpe in cheatPivotEntries])
            [legitGameAnalyses.extend(ga) for ga in self.env.gameAnalysisDB.byUserIds([u.id for u in legits])]
        else:
            logging.debug("getting players by engine")
            cheats = self.env.playerDB.byEngine(True)
            legits = self.env.playerDB.byEngine(False)

            shuffle(cheats)
            shuffle(legits)

            cheatGameAnalyses = []
            legitGameAnalyses = []

            logging.debug("getting game analyses from DB")
            [cheatGameAnalyses.extend(ga) for ga in self.env.gameAnalysisDB.byUserIds([u.id for u in cheats])]
            [legitGameAnalyses.extend(ga) for ga in self.env.gameAnalysisDB.byUserIds([u.id for u in legits])]

        logging.debug("building moveAnalysisTensors")
        cheatGameTensors = [tga.moveAnalysisTensors() for tga in cheatGameAnalyses if tga.gameLength() <= 60]
        legitGameTensors = [tga.moveAnalysisTensors() for tga in legitGameAnalyses if tga.gameLength() <= 60]

        logging.debug("batching tensors")
        return self.createBatchAndLabels(cheatGameTensors, legitGameTensors)

    @staticmethod
    def createBatchAndLabels(cheatBatch, legitBatch):
        # group the dataset into batches by the length of the dataset, because numpy needs it that way
        mlen = min(len(cheatBatch), len(legitBatch))

        cheats = cheatBatch[:mlen]
        legits = legitBatch[:mlen]

        logging.debug("batch size " + str(len(cheats + legits)))

        labels = [1.0]*len(cheats) + [0.0]*len(legits)

        blz = list(zip(cheats+legits, labels))
        shuffle(blz)

        return {
            'data': np.array([t for t, l in blz]),
            'labels': [
                np.array([l for t, l in blz]), 
                np.array([[[l]]*(len(t)-13) for t, l in blz]),
                np.array([[[l]]*(len(t)-4) for t, l in blz])
            ]
        }