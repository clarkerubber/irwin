from default_imports import *

from conf.ConfigWrapper import ConfigWrapper

import numpy as np
import logging
import os

from random import shuffle
from math import ceil

from modules.game.AnalysedGame import GameAnalysedGame

from keras.models import load_model, Model
from keras.layers import Dropout, Embedding, Reshape, Dense, LSTM, Input, concatenate, Conv1D, Flatten
from keras.optimizers import Adam

from keras.engine.training import Model

from numpy import ndarray

GamePrediction = NewType('GamePrediction', int)
MovePrediction = NewType('MovePrediction', int)

WeightedMovePrediction = NewType('WeightedMovePrediction', int)
WeightedGamePrediction = NewType('WeightedGamePrediction', int)

class AnalysedGamePrediction(NamedTuple('AnalysedGamePrediction', [
        ('game', GamePrediction),
        ('lstmMoves', List[MovePrediction]),
        ('isolatedMoves', List[MovePrediction])
    ])):
    @staticmethod
    def fromTensor(tensor: ndarray, length: int):
        return AnalysedGamePrediction(
            game = int(100*tensor[0][0]),
            lstmMoves = [int(100*i) for i in tensor[1][0][:length]],
            isolatedMoves = [int(100*i) for i in tensor[2][0][:length]])

    def weightedMovePredictions(self) -> List[WeightedMovePrediction]:
        return [int(0.5*(l + i)) for l, i in zip(self.lstmMoves, self.isolatedMoves)]
    
    def weightedGamePrediction(self) -> WeightedGamePrediction:
        moveActivations = sorted(self.weightedMovePredictions(), reverse=True)
        moveActivationsLen = len(moveActivations)

        nanToZero = lambda x: 0 if np.isnan(x) else x

        highest = nanToZero(np.average([i for i in moveActivations if i > 80]))
        topX = np.average(moveActivations[:ceil(0.3*moveActivationsLen)])
        topY = np.average(moveActivations[:ceil(0.9*moveActivationsLen)])

        return int(np.average([highest, topX, topY]))

class AnalysedGameModel:
    def __init__(self, config: ConfigWrapper, newmodel: bool = False):
        self.config = config
        self.model = self.createModel(newmodel)
    
    def createModel(self, newmodel: bool = False) -> Model:
        if os.path.isfile(self.config["irwin model analysed file"]) and not newmodel:
            logging.debug("model already exists, opening from file")
            m = load_model(self.config["irwin model analysed file"])
            m._make_predict_function()
            return m
        logging.debug('model does not exist, building from scratch')
        inputGame = Input(shape=(60, 18), dtype='float32', name='game_input')
        pieceType = Input(shape=(60, 1), dtype='float32', name='piece_type')

        pieceEmbed = Embedding(input_dim=7, output_dim=8)(pieceType)
        rshape = Reshape((60,8))(pieceEmbed)

        concats = concatenate(inputs=[inputGame, rshape])

        # Merge embeddings

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
        # merge move stats with move options
        c1 = Conv1D(filters=128, kernel_size=5, name='conv1')(concats)

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

        model = Model(inputs=[inputGame, pieceType], outputs=[mainOutput, lstmMove, isolatedMove])

        model.compile(optimizer=Adam(lr=0.0001),
            loss='binary_crossentropy',
            loss_weights=[1., 0.3, 0.2],
            metrics=['accuracy'])
        return model

    def predict(self, gameAnalysedGames: List[GameAnalysedGame]) -> List[Opt[ndarray]]:
        list_to_array = lambda l: None if l is None else [np.array([l[0]]), np.array([l[1]])]
        arrs = ((list_to_array(ag.tensor()), ag.length()) for ag in gameAnalysedGames)
        return [None if t is None else AnalysedGamePrediction.fromTensor(self.model.predict(t), l) for t, l in arrs]

    def saveModel(self):
        self.model.save(self.config["irwin model analysed file"])