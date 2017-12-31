import numpy as np
import logging
import os

from pprint import pprint

from random import shuffle
from decimal import Decimal
from math import log

from collections import namedtuple

from keras.models import load_model, Sequential
from keras.layers import Dense, Activation
from keras.optimizers import Adam

from modules.core.GameAnalysisStore import GameAnalysisStore

class PlayerModel(namedtuple('BinaryGameModel', ['env'])):
  def model(self, newmodel=False):
    if os.path.isfile('modules/irwin/models/playerBinary.h5') and not newmodel:
      print("model already exists, opening from file")
      return load_model('modules/irwin/models/playerBinary.h5')
    print('model does not exist, building from scratch')

    model = Sequential([
      Dense(32, input_shape=(31,)),
      Activation('relu'),
      Dense(16),
      Activation('sigmoid'),
      Dense(8),
      Activation('softmax'),
      Dense(1),
      Activation('sigmoid')
    ])

    model.compile(optimizer=Adam(),
      loss='binary_crossentropy',
      metrics=['accuracy'])

    return model

  def train(self, batchSize, epochs, newmodel=False):
    # get player sample
    print("getting model")
    model = self.model(newmodel)
    print("getting dataset")
    batch = self.getTrainingDataset()

    print("training")
    print("samples: " + str(len(batch['batch'])))
    model.fit(batch['batch'], batch['labels'], epochs=epochs, batch_size=32, validation_split=0.2)
    self.saveModel(model)
    print("complete")

  def saveModel(self, model):
    print("saving model")
    model.save('modules/irwin/models/playerBinary.h5')

  def getTrainingDataset(self):
    legitPGAs = self.env.playerGameActivationsDB.byEngine(False)
    cheatPGAs = self.env.playerGameActivationsDB.byEngine(True)

    legitGameAnalyses = self.env.gameAnalysisDB.byUserIds([pga.userId for pga in legitPGAs])
    cheatGameAnalyses = self.env.gameAnalysisDB.byUserIds([pga.userId for pga in cheatPGAs])

    legitZip = list(zip(legitPGAs, legitGameAnalyses))
    cheatZip = list(zip(cheatPGAs, cheatGameAnalyses))

    shuffle(legitZip)
    shuffle(cheatZip)

    mlen = min(len(legitPGAs), len(cheatPGAs))

    legitZip = legitZip[:mlen]
    cheatZip = cheatZip[:mlen]

    legits = [PlayerModel.binPGAs(pgas) + (GameAnalysisStore([], gas).playerTensor()) for pgas, gas in legitZip]
    cheats = [PlayerModel.binPGAs(pgas) + (GameAnalysisStore([], gas).playerTensor()) for pgas, gas in cheatZip]

    labels = [1]*len(cheats) + [0]*len(legits)

    blz = list(zip(cheats + legits, labels))

    shuffle(blz)

    return {
      'batch': np.array([a for a, b in blz]),
      'labels': np.array([b for a, b in blz])
    }

  def predict(self, generalActivations, narrowActivations, playerTensor, model=None):
    if model is None:
      model = self.model()
    data = PlayerModel.binActivations(zip(generalActivations, narrowActivations))+playerTensor
    p = model.predict(np.array([data
      ]))
    return int(100*p[0][0])

  @staticmethod
  def binActivations(activations):
    activations = list(activations)
    logs = [float(10*Decimal(i*j).ln()) for i, j in activations]
    bins = [(35, 40), (40, 45), (45, 50), (50, 55), (55, 60), (60, 70), (70, 80), (80, 90), (90, 100)]
    return [len([1 for x in logs if x>i and x<=j]) for i, j in bins]

  @staticmethod
  def binPGAs(pgas):
    return PlayerModel.binActivations(zip(pgas.generalActivations, pgas.narrowActivations))