import numpy as np
import logging
import os

from pprint import pprint

from random import shuffle

from collections import namedtuple

from keras.models import load_model, Model
from keras.layers import Embedding, Dropout, Dense, Reshape, LSTM, Input, concatenate, Conv1D
from keras.optimizers import Adam

from functools import lru_cache

class GameModel(namedtuple('GameModel', ['env'])):
  @lru_cache(maxsize=2)
  def model(self, newmodel=False):
    if os.path.isfile('modules/irwin/models/game.h5') and not newmodel:
      print("model already exists, opening from file")
      return load_model('modules/irwin/models/game.h5')
    print('model does not exist, building from scratch')

    moveStatsInput = Input(shape=(None, 5), dtype='float32', name='move_input')

    mv1 = Dense(32, activation='relu')(moveStatsInput)
    d1 = Dropout(0.3)(mv1)
    mv2 = Dense(16, activation='relu')(d1)

    c1 = Conv1D(filters=64, kernel_size=5, name='conv1')(mv2)

    # analyse all the moves and come to a decision about the game
    l1 = LSTM(64, return_sequences=True)(c1)
    l2 = LSTM(32, return_sequences=True, activation='relu')(l1)

    c2 = Conv1D(filters=64, kernel_size=10, name='conv2')(l2)

    l3 = LSTM(32, return_sequences=True)(c2)
    l4 = LSTM(16, return_sequences=True, activation='sigmoid')(l3)
    l5 = LSTM(8)(l4)
    l6 = Dense(8, activation='sigmoid', name='game_word')(l5)
    d4 = Dropout(0.3)(l6)
    l6 = Dense(1, activation='sigmoid')(d4)

    mainOutput = Dense(1, activation='sigmoid', name='main_output')(l6)

    model = Model(inputs=moveStatsInput, outputs=mainOutput)

    model.compile(optimizer=Adam(lr=0.0001),
      loss='binary_crossentropy',
      metrics=['accuracy'])
    return model

  def train(self, epochs, newmodel=False):
    # get player sample
    print("getting model")
    model = self.model(newmodel)
    print("getting dataset")
    batch = self.getTrainingDataset()

    print("training")
    print("Batch Info: Games: " + str(len(batch['data'])))

    model.fit(batch['data'], batch['labels'], epochs=epochs, batch_size=32, validation_split=0.2)

    self.saveModel(model)
    print("complete")

  def saveModel(self, model):
    print("saving model")
    model.save('modules/irwin/models/game.h5')

  def getTrainingDataset(self):
    print("Getting players from DB")
    cheats = self.env.playerDB.byEngine(True)
    legits = self.env.playerDB.byEngine(False)

    cheatTensors = []
    legitTensors = []

    print("Getting games from DB")
    for p in legits + cheats:
      if p.engine:
        cheatTensors.extend([g.tensor(p.id) for g in self.env.gameDB.byUserId(p.id)])
      else:
        legitTensors.extend([g.tensor(p.id) for g in self.env.gameDB.byUserId(p.id)])

    cheatTensors = [t for t in cheatTensors if t is not None]
    legitTensors = [t for t in legitTensors if t is not None]

    shuffle(cheatTensors)
    shuffle(legitTensors)

    print("batching tensors")
    return self.createBatchAndLabels(cheatTensors, legitTensors)

  @staticmethod
  def createBatchAndLabels(cheatBatch, legitBatch):
    # group the dataset into batches by the length of the dataset, because numpy needs it that way
    mlen = min(len(cheatBatch), len(legitBatch))

    cheats = cheatBatch[:mlen]
    legits = legitBatch[:mlen]

    print("batch size " + str(len(cheats + legits)))

    labels = [1]*len(cheats) + [0]*len(legits)

    blz = list(zip(cheats+legits, labels))
    shuffle(blz)

    return {
      'data': np.array([t for t, l in blz]),
      'labels': np.array([l for t, l in blz])
    }