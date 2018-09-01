from default_imports import *

from conf.ConfigWrapper import ConfigWrapper

import numpy as np
import logging
import os

from random import shuffle

from collections import namedtuple

from modules.game.Player import PlayerID
from modules.game.Game import Game

from keras.models import load_model, Model
from keras.layers import Dropout, Embedding, Reshape, Flatten, Dense, LSTM, Input, concatenate, Conv1D
from keras.optimizers import Adam
from keras.callbacks import TensorBoard

from functools import lru_cache

class BasicGameModel:
    def __init__(self, config: ConfigWrapper, newmodel: bool = False):
        self.config = config
        self.model = self.createModel(newmodel)

    def createModel(self, newmodel: bool = False):
        if os.path.isfile(self.config["irwin model basic file"]) and not newmodel:
            logging.debug("model already exists, opening from file")
            return load_model(self.config["irwin model basic file"])
        logging.debug('model does not exist, building from scratch')

        moveStatsInput = Input(shape=(60, 8), dtype='float32', name='move_input')
        pieceType = Input(shape=(60, 1), dtype='float32', name='piece_type')

        pieceEmbed = Embedding(input_dim=7, output_dim=8)(pieceType)
        rshape = Reshape((60,8))(pieceEmbed)

        concats = concatenate(inputs=[moveStatsInput, rshape])

        ### Conv Net Block of Siamese Network
        conv1 = Conv1D(filters=64, kernel_size=3, activation='relu')(concats)
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
        mv1 = Dense(32, activation='relu')(concats)
        d1 = Dropout(0.3)(mv1)
        mv2 = Dense(16, activation='relu')(d1)

        c1 = Conv1D(filters=64, kernel_size=5, name='conv1')(mv2)

        # analyse all the moves and come to a decision about the game
        l1 = LSTM(64, return_sequences=True)(c1)
        l2 = LSTM(32, return_sequences=True, activation='relu')(l1)

        c2 = Conv1D(filters=64, kernel_size=10, name='conv2')(l2)

        l3 = LSTM(32, return_sequences=True)(c2)
        l4 = LSTM(16, return_sequences=True, activation='relu', recurrent_activation='hard_sigmoid')(l3)
        l5 = LSTM(16, activation='sigmoid')(l4)

        mergeLSTMandConv = concatenate([l5, convNetOutput])
        denseOut1 = Dense(16, activation='sigmoid')(mergeLSTMandConv)
        mainOutput = Dense(1, activation='sigmoid', name='main_output')(denseOut1)

        model = Model(inputs=[moveStatsInput, pieceType], outputs=mainOutput)

        model.compile(optimizer=Adam(lr=0.0001),
            loss='binary_crossentropy',
            metrics=['accuracy'])
        return model

    def predict(self, playerId: PlayerID, games: List[Game]) -> Opt[int]:
        tensors = [game.tensor(playerId) for game in games]
        return [None if t is None else int(100*self.model.predict([np.array([t[0]]),np.array([t[1]])])[0][0]) for t in tensors]

    def saveModel(self):
        logging.debug("saving model")
        self.model.save(self.config["irwin model basic file"])