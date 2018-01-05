import numpy as np
import logging
import os

from pprint import pprint

from random import shuffle
from decimal import Decimal
from math import log

from collections import namedtuple, Counter

from keras.models import load_model, Sequential
from keras.layers import Dense, Activation
from keras.optimizers import Adam

from modules.core.GameAnalysisStore import GameAnalysisStore

from modules.irwin.PlayerGameWords import PlayerGameWords

class PlayerModel(namedtuple('BinaryGameModel', ['env'])):
  def model(self, newmodel=False):
    if os.path.isfile('modules/irwin/models/playerBinary.h5') and not newmodel:
      print("model already exists, opening from file")
      return load_model('modules/irwin/models/playerBinary.h5')
    print('model does not exist, building from scratch')

    vocabSize = self.buildVocabularly()

    model = Sequential([
      Dense(32+int(vocabSize/2), input_shape=(31+vocabSize,)),
      Activation('relu'),
      Dense(16+int(vocabSize/3)),
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

  def buildVocabularly(self):
    print("Building Vocabularly")
    print("Getting Player Game Activations")
    allPGAs = self.env.playerGameActivationsDB.all()
    length = str(len(allPGAs))
    print("Got " + length)
    words = {
      'narrowPositionWords': Counter(),
      'generalPositionWords': Counter(),
      'narrowGameWords': Counter(),
      'generalGameWords': Counter()
    }
    for i, pga in enumerate(allPGAs):
      words['narrowPositionWords'] =  Counter(pga.narrowIntermediateActivations['positions']) + words['narrowPositionWords']
      words['generalPositionWords'] =  Counter(pga.generalIntermediateActivations['positions']) + words['generalPositionWords']
      words['narrowGameWords'] =  Counter(pga.narrowIntermediateActivations['games']) + words['narrowGameWords']
      words['generalGameWords'] =  Counter(pga.generalIntermediateActivations['games']) + words['generalGameWords']

    a = [int(word) for word, amount in words['narrowPositionWords'].most_common() if amount > 200]
    b = [int(word) for word, amount in words['generalPositionWords'].most_common() if amount > 200]
    c = [int(word) for word, amount in words['narrowGameWords'].most_common() if amount > 200]
    d = [int(word) for word, amount in words['generalGameWords'].most_common() if amount > 200]

    a.sort()
    b.sort()
    c.sort()
    d.sort()

    output = {
      'narrowPositionWords': a,
      'generalPositionWords': b,
      'narrowGameWords': c,
      'generalGameWords': d
    }

    self.env.playerGameWordsDB.write(PlayerGameWords(
      narrowPositionWords = a,
      generalPositionWords = b,
      narrowGameWords = c,
      generalGameWords = d))

    return len(a)+len(b)+len(c)+len(d)

  def getTrainingDataset(self):
    words = self.env.playerGameWordsDB.newest()

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

    legits = [PlayerModel.tensorPGA(pga, words) + (GameAnalysisStore([], gas).playerTensor()) for pga, gas in legitZip]
    cheats = [PlayerModel.tensorPGA(pga, words) + (GameAnalysisStore([], gas).playerTensor()) for pga, gas in cheatZip]

    labels = [1]*len(cheats) + [0]*len(legits)

    blz = list(zip(cheats + legits, labels))

    shuffle(blz)

    return {
      'batch': np.array([a for a, b in blz]),
      'labels': np.array([b for a, b in blz])
    }

  def predict(self, playerGameActivations, playerTensor, model=None, words=None):
    if model is None:
      model = self.model()
    if words is None:
      words = self.env.playerGameWordsDB.newest()
    data = PlayerModel.tensorPGA(playerGameActivations, words)+playerTensor
    p = model.predict(np.array([data]))
    return int(100*p[0][0])

  @staticmethod
  def binActivations(activations):
    bins = [(0, 10), (10, 20), (20, 30), (30, 40), (40, 50), (50, 60), (60, 70), (70, 80), (90, 100)]
    return [len([1 for x in activations if x>i and x<=j]) for i, j in bins]

  @staticmethod
  def wordTensor(pga, words):
    generalPositions = [pga.generalIntermediateActivations['positions'].get(str(word), 0) for word in words.generalPositionWords]
    narrowPositions = [pga.narrowIntermediateActivations['positions'].get(str(word), 0) for word in words.narrowPositionWords]

    generalGames = [pga.generalIntermediateActivations['games'].get(str(word), 0) for word in words.generalGameWords]
    narrowGames = [pga.narrowIntermediateActivations['games'].get(str(word), 0) for word in words.narrowGameWords]

    return generalPositions + narrowPositions + generalGames + narrowGames

  @staticmethod
  def tensorPGA(pga, words):
    return PlayerModel.binActivations(pga.avgGameActivations) + PlayerModel.wordTensor(pga, words)