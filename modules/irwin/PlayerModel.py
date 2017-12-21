import numpy as np
import logging
import os

from pprint import pprint

from random import shuffle

from collections import namedtuple

from keras.models import load_model, Sequential
from keras.layers import Dense, Activation
from keras.optimizers import Adam

class PlayerModel(namedtuple('BinaryGameModel', ['env'])):
  def model(self, newmodel=False):
    if os.path.isfile('modules/irwin/models/playerBinary.h5') and not newmodel:
      print("model already exists, opening from file")
      return load_model('modules/irwin/models/playerBinary.h5')
    print('model does not exist, building from scratch')

    model = Sequential([
      Dense(32, input_shape=(5,)),
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
    enginePGAs = self.env.playerGameActivationsDB.byEngine(True)

    shuffle(legitPGAs)
    shuffle(enginePGAs)

    mlen = min(len(legitPGAs), len(enginePGAs))

    legitPGAs = legitPGAs[:mlen]
    enginePGAs = enginePGAs[:mlen]

    legits = [PlayerModel.binPGAs(pgas) for pgas in legitPGAs]
    engines = [PlayerModel.binPGAs(pgas) for pgas in enginePGAs]

    labels = [1]*len(engines) + [0]*len(legits)

    blz = list(zip(engines + legits, labels))

    return {
      'batch': np.array([a for a, b in blz]),
      'labels': np.array([b for a, b in blz])
    }

  def predict(self, activations, model=None):
    if model is None:
      model = self.model()
    data = PlayerModel.binActivations(activations)
    p = model.predict(np.array([data]))
    return int(100*p[0][0])

  @staticmethod
  def binActivations(activations):
    return np.array([len([i for i in activations if i > x and i <= y]) for x, y in [(90, 100), (75, 90), (50, 75), (25, 50), (-1, 25)]]) # count by brackets

  @staticmethod
  def binPGAs(pgas):
    return PlayerModel.binActivations(pgas.activations)