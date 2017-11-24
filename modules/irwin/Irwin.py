from collections import namedtuple
from pprint import pprint
from random import shuffle

import logging
import numpy as np
import os.path

from modules.irwin.TrainingStats import TrainingStats, Accuracy, Sample
from modules.irwin.FalseReports import FalseReport

from keras.models import Sequential, load_model
from keras.layers import Conv1D, Dense, Dropout, Embedding, LSTM


class Irwin(namedtuple('Irwin', ['env', 'config'])):
  def gameModel(self):
    if os.path.isfile('modules/irwin/models/game.h5'):
      print("model already exists, opening from file")
      return load_model('modules/irwin/models/game.h5')
    print('model does not exist, building from scratch')
    model = Sequential()
    model.add(Conv1D(filters=32, kernel_size=32, padding='causal',
        activation='sigmoid', input_shape=(None,10)))
    model.add(LSTM(32, return_sequences=True))
    model.add(LSTM(32, return_sequences=True))
    model.add(LSTM(32))
    model.add(Dense(64, activation='relu'))
    model.add(Dense(32, activation='relu'))
    model.add(Dense(16, activation='relu'))
    model.add(Dense(1, activation='sigmoid'))
    model.compile(optimizer='rmsprop',
      loss='binary_crossentropy',
      metrics=['accuracy'])
    return model

  def saveGameModel(self, model):
    print("saving model")
    model.save('modules/irwin/models/game.h5')

  def getDataset(self):
    print("getting players", end="...", flush=True)
    players = self.env.playerDB.balancedSample(self.config['train']['batchSize'])
    print(" %d" % len(players))
    print("getting game analyses", end="...", flush=True)
    gameAnalyses = []
    [gameAnalyses.extend(self.env.gameAnalysisDB.byUserId(p.id)) for p in players]
    print(" %d" % len(gameAnalyses))

    print("assigning labels")
    gameLabels = self.assignLabels(gameAnalyses, players)

    print("splitting game analyses datasets")
    cheatGameAnalyses = gameAnalyses[:sum(gameLabels)]
    legitGameAnalyses = gameAnalyses[sum(gameLabels):]

    print("getting moveAnalysisTensors")
    cheatGameTensors = [tga.moveAnalysisTensors() for tga in cheatGameAnalyses]
    legitGameTensors = [tga.moveAnalysisTensors() for tga in legitGameAnalyses]

    return Irwin.createBatchAndLabels(cheatGameTensors, legitGameTensors)


  def train(self):
    # get player sample
    print("getting model")
    model = self.gameModel()
    print("getting dataset")
    batches = self.getDataset()

    print("training")
    for b in batches:
      print("Batch Info: Games: " + str(len(b['batch'])))
      print("Game Len: " + str(len(b['batch'][0])))
      model.fit(b['batch'], b['labels'], epochs=self.config['train']['cycles'], batch_size=32, validation_split=0.2)
      self.saveGameModel(model)
    print("complete")

  @staticmethod
  def getGameEngineStatus(gameAnalysis, players):
    return any([p for p in players if gameAnalysis.userId == p.id and p.engine])

  @staticmethod
  def assignLabels(gameAnalyses, players):
    return [int(Irwin.getGameEngineStatus(gameAnalysis, players)) for gameAnalysis in gameAnalyses]

  @staticmethod
  def createBatchAndLabels(cheatBatch, legitBatch):
    batches = []
    # group the dataset into batches by the length of the dataset, because numpy needs it that way
    for x in range(22, 40):
      cheats = list([r for r in cheatBatch if len(r) == x])
      legits = list([r for r in legitBatch if len(r) == x])

      print("Legits Batch Size: " + str(len(legits)))
      print("Cheats Batch Size: " + str(len(cheats)))

      # only make the batch trainable if it's big
      if len(cheats + legits) > 32:
        batches.append({
          'batch': np.array(cheats + legits),
          'labels': np.array([1]*len(cheats) + [0]*len(legits))
        })
    shuffle(batches)
    return batches
