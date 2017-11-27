from collections import namedtuple
from pprint import pprint
from random import shuffle

import logging
import numpy as np
import os.path

from modules.irwin.TrainingStats import TrainingStats, Accuracy, Sample
from modules.irwin.FalseReports import FalseReport

from keras.models import load_model, Model
from keras.layers import Dropout, Dense, LSTM, Input, concatenate
from keras.optimizers import Adam


class Irwin(namedtuple('Irwin', ['env', 'config'])):
  def gameModel(self):
    if os.path.isfile('modules/irwin/models/game.h5'):
      print("model already exists, opening from file")
      return load_model('modules/irwin/models/game.h5')
    print('model does not exist, building from scratch')

    gameStatsInput = Input(shape=(4,), dtype='float32', name='game_stats_input')
    pvInput = Input(shape=(None, 10), dtype='float32', name='pv_input')
    moveStatsInput = Input(shape=(None, 9), dtype='float32', name='move_input')

    g1 = Dense(16, activation='relu')(gameStatsInput)
    g2 = Dense(16, activation='relu')(g1)
    g3 = Dense(16, activation='sigmoid')(g2)

    pv1 = Dense(64, activation='relu')(pvInput)
    pv2 = Dense(64, activation='relu')(pv1)
    pv3 = Dense(32, activation='relu')(pv2)
    pv4 = Dense(16, activation='sigmoid')(pv3)

    mv1 = Dense(64, activation='relu')(moveStatsInput)
    mv2 = Dense(64, activation='relu')(mv1)
    mv3 = Dense(32, activation='relu')(mv2)
    mv4 = Dense(16, activation='sigmoid')(mv3)

    mvpv = concatenate([mv4, pv4])

    l1 = LSTM(64, return_sequences=True)(mvpv)
    l2 = LSTM(64, return_sequences=True)(l1)
    l3 = LSTM(32)(l2)
    l4 = Dense(32, activation='relu')(l3)
    l5 = Dense(16, activation='sigmoid')(l4)

    c1 = concatenate([l5, g3])

    c2 = Dense(32, activation='relu')(c1)
    c3 = Dense(16, activation='relu')(c2)
    c4 = Dense(16, activation='tanh')(c3)

    mainOutput = Dense(1, activation='sigmoid', name='main_output')(c4)

    m1 = Dense(64, activation='relu')(l2)
    m2 = Dense(32, activation='relu')(m1)
    m3 = Dense(32, activation='relu')(m2)
    secondaryOutput = Dense(1, activation='sigmoid', name='secondary_output')(m3)

    model = Model(inputs=[gameStatsInput, pvInput, moveStatsInput], outputs=[mainOutput, secondaryOutput])

    model.compile(optimizer=Adam(),
      loss='binary_crossentropy',
      loss_weights=[1., 0.2],
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
    for x in range(5):
      for b in batches:
        print("Batch Info: Games: " + str(len(b['batch'][0])))
        print("Game Len: " + str(len(b['batch'][2][0])))
        model.fit(b['batch'], b['labels'], epochs=self.config['train']['cycles'], batch_size=32, validation_split=0.2)
        self.saveGameModel(model)
      shuffle(batches)
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
    for x in range(22, 34):
      cheats = list([r for r in cheatBatch if len(r[1]) == x])
      legits = list([r for r in legitBatch if len(r[1]) == x])

      mlen = min(len(cheats), len(legits))

      cheats = cheats[:mlen]
      legits = legits[:mlen]

      # only make the batch trainable if it's big
      if len(cheats + legits) > 1000:
        gameStats = np.array([p[0] for p in (cheats + legits)])
        pvs = np.array([[m[0] for m in p[1]] for p in (cheats + legits)])
        moveStats = np.array([[m[1] for m in p[1]] for p in (cheats + legits)])

        b = [gameStats, pvs, moveStats]
        l = [
          np.array([1]*len(cheats) + [0]*len(legits)), 
          np.array([[[1]]*len(moveStats[0])]*len(cheats) + [[[0]]*len(moveStats[0])]*len(legits))
        ]
        batches.append({
          'batch': b,
          'labels': l
        })
    shuffle(batches)
    return batches

  @staticmethod
  def flatten(l):
    return [item for sublist in l for item in sublist]