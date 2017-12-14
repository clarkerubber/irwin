import numpy as np
import logging
import os

from random import shuffle

from collections import namedtuple

from keras.models import load_model, Model
from keras.layers import Embedding, Dropout, Dense, Reshape, LSTM, Input, concatenate, Conv1D
from keras.optimizers import Adam

class BinaryGameModel(namedtuple('BinaryGameModel', ['env', 'type'])):
  def model(self, newmodel=False):
    if self.type == 'general':
      if os.path.isfile('modules/irwin/models/gameBinary.h5') and not newmodel:
        print("model already exists, opening from file")
        return load_model('modules/irwin/models/gameBinary.h5')
    elif self.type == 'narrow':
      if os.path.isfile('modules/irwin/models/gameBinaryNarrow.h5') and not newmodel:
        print("model already exists, opening from file")
        return load_model('modules/irwin/models/gameBinaryNarrow.h5')
    print('model does not exist, building from scratch')
    pvInput = Input(shape=(None, 10), dtype='float32', name='pv_input')
    moveStatsInput = Input(shape=(None, 6), dtype='float32', name='move_input')

    advInput = Input(shape=(None,), dtype='int32', name='advantage_input')
    ranksInput = Input(shape=(None,), dtype='int32', name='ranks_input')
    moveNumberInput = Input(shape=(None,), dtype='int32', name='move_number_input')
    ambiguityInput = Input(shape=(None,), dtype='int32', name='ambiguity_input')

    # Embed rank and move number
    a1 = Embedding(input_dim=41, output_dim=32)(advInput)
    r1 = Embedding(input_dim=16, output_dim=16)(ranksInput)
    mn1 = Embedding(input_dim=61, output_dim=32)(moveNumberInput)
    am1 = Embedding(input_dim=6, output_dim=16)(ambiguityInput)

    # Merge embeddings
    mnr1 = concatenate([r1, mn1, a1, am1])
    mnr2 = Reshape((-1, 96))(mnr1)

    # analyse PV data (potential moves)
    pv1 = Dense(128, activation='relu')(pvInput)
    pv2 = Dense(64, activation='relu')(pv1)
    d2 = Dropout(0.3)(pv2)
    pv4 = Dense(32, activation='sigmoid')(d2)

    # join rank and move embeddings with move info
    mv0 = concatenate([mnr2, moveStatsInput])

    # analyse move stats and embeddings prior to LSTM
    mv1 = Dense(128, activation='relu')(mv0)
    mv2 = Dense(64, activation='relu')(mv1)
    mv3 = Dense(64, activation='relu')(mv2)
    d3 = Dropout(0.3)(mv3)
    mv4 = Dense(16, activation='sigmoid')(d3)

    # merge move stats with move options
    mvpv = concatenate([mv4, pv4])

    c = Conv1D(filters=128, kernel_size=5, padding='same', name='conv')(mvpv)

    # analyse all the moves and come to a decision about the game
    l1 = LSTM(128, return_sequences=True)(c)
    l2 = LSTM(128, return_sequences=True)(l1)
    l3 = LSTM(64, return_sequences=True)(l2)
    l4 = LSTM(64)(l3)
    l5 = Dense(64, activation='relu')(l4)
    d4 = Dropout(0.3)(l5)
    l6 = Dense(1, activation='sigmoid')(d4)

    secondaryOutput = Dense(1, activation='sigmoid', name='secondary_output')(l3)

    mainOutput = Dense(1, activation='sigmoid', name='main_output')(l6)

    model = Model(inputs=[pvInput, moveStatsInput, moveNumberInput, ranksInput, advInput, ambiguityInput], outputs=[mainOutput, secondaryOutput])

    model.compile(optimizer=Adam(lr=0.0001),
      loss='binary_crossentropy',
      loss_weights=[1., 0.3],
      metrics=['accuracy'])
    return model

  def train(self, batchSize, epochs, newmodel=False):
    # get player sample
    print("getting model")
    model = self.model(newmodel)
    print("getting dataset")
    batches = self.getTrainingDataset()

    print("training")
    for x in range(2):
      for b in batches:
        print("Batch Info: Games: " + str(len(b['batch'][0])))
        print("Game Len: " + str(len(b['batch'][2][0])))
        model.fit(b['batch'], b['labels'], epochs=epochs, batch_size=32, validation_split=0.2)
        self.saveModel(model)
      shuffle(batches)
    print("complete")

  def saveModel(self, model):
    print("saving model")
    if self.type == 'general':
      model.save('modules/irwin/models/gameBinary.h5')
    if self.type == 'narrow':
      model.save('modules/irwin/models/gameBinaryNarrow.h5')

  def getTrainingDataset(self):
    if self.type == 'general':
      cheatGameAnalyses = []
      legitGameAnalyses = []
      for length in range(20, 60):
        print("gettings games of length: " + str(length))
        cheatPivotEntries = self.env.gameAnalysisPlayerPivotDB.byEngineAndLength(True, length)
        legitPivotEntries = self.env.gameAnalysisPlayerPivotDB.byEngineAndLength(False, length)

        print("got: "+str(len(cheatPivotEntries + legitPivotEntries)))

        shuffle(cheatPivotEntries)
        shuffle(legitPivotEntries)

        minEntries = min(len(cheatPivotEntries), len(legitPivotEntries))
        sampleSize = min(int(self.env.settings['irwin']['train']['batchSize']/2), minEntries)

        cheatGameAnalyses.extend(self.env.gameAnalysisDB.byIds([cpe.id for cpe in cheatPivotEntries[:sampleSize]]))
        legitGameAnalyses.extend(self.env.gameAnalysisDB.byIds([lpe.id for lpe in legitPivotEntries[:sampleSize]]))

      print("getting moveAnalysisTensors")
      cheatGameTensors = [tga.moveAnalysisTensors() for tga in cheatGameAnalyses]
      legitGameTensors = [tga.moveAnalysisTensors() for tga in legitGameAnalyses]

      print("batching tensors")
      return self.createBatchAndLabels(cheatGameTensors, legitGameTensors)
    elif self.type == 'narrow':
      cheatGameAnalyses = []
      legitGameAnalyses = []
      unclearGameAnalyses = []
      for length in range(20, 60):
        print("gettings games of length: " + str(length))
        cheatPivotEntries = self.env.confidentGameAnalysisPivotDB.byEngineLengthAndPrediction(True, length, 80)
        legitPivotEntries = self.env.confidentGameAnalysisPivotDB.byEngineLengthAndPrediction(False, length, 30)
        unclearPivotEntries = self.env.confidentGameAnalysisPivotDB.byPredictionRangeAndLength(40, 60, length)

        print("got: "+str(len(cheatPivotEntries + legitPivotEntries + unclearPivotEntries)))

        shuffle(cheatPivotEntries)
        shuffle(legitPivotEntries)
        shuffle(unclearPivotEntries)

        minEntries = min(len(cheatPivotEntries), len(legitPivotEntries), len(unclearPivotEntries))
        sampleSize = min(int(self.env.settings['irwin']['train']['batchSize']/2), minEntries)

        cheatGameAnalyses.extend(self.env.gameAnalysisDB.byIds([cpe.id for cpe in cheatPivotEntries[:sampleSize]]))
        legitGameAnalyses.extend(self.env.gameAnalysisDB.byIds([lpe.id for lpe in legitPivotEntries[:sampleSize]]))
        unclearGameAnalyses.extend(self.env.gameAnalysisDB.byIds([lpe.id for lpe in unclearPivotEntries[:sampleSize]]))

      print("getting moveAnalysisTensors")
      cheatGameTensors = [tga.moveAnalysisTensors() for tga in cheatGameAnalyses]
      legitGameTensors = [tga.moveAnalysisTensors() for tga in legitGameAnalyses]
      unclearGameTensors = [tga.moveAnalysisTensors() for tga in unclearGameAnalyses]

      print("batching tensors")
      return self.createBatchAndLabels(cheatGameTensors, legitGameTensors + unclearGameTensors)

  @staticmethod
  def createBatchAndLabels(cheatBatch, legitBatch):
    batches = []
    # group the dataset into batches by the length of the dataset, because numpy needs it that way
    for x in range(20, 60):
      cheats = list([r for r in cheatBatch if len(r) == x])
      legits = list([r for r in legitBatch if len(r) == x])

      mlen = min(len(cheats), len(legits))

      cheats = cheats[:mlen]
      legits = legits[:mlen]

      cl = [True]*len(cheats) + [False]*len(legits)

      blz = list(zip(cheats+legits, cl))
      shuffle(blz)

      # only make the batch trainable if it's big
      if len(cheats + legits) > 800:
        pvs =         np.array([[m[0] for m in p[0]] for p in blz])
        moveStats =   np.array([[m[1] for m in p[0]] for p in blz])
        moveNumbers = np.array([[m[2] for m in p[0]] for p in blz])
        ranks =       np.array([[m[3] for m in p[0]] for p in blz])
        advs =        np.array([[m[4] for m in p[0]] for p in blz])
        ambs =        np.array([[m[5] for m in p[0]] for p in blz])

        b = [pvs, moveStats, moveNumbers, ranks, advs, ambs]
        l = [
          np.array([int(i[1]) for i in blz]), 
          np.array([[[0]]*5 + [[int(i[1])]]*(len(moveStats[0])-5) for i in blz])
        ]

        batches.append({
          'batch': b,
          'labels': l
        })
    shuffle(batches)
    return batches