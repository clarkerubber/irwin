import numpy as np
import logging
import os

from random import shuffle

from collections import namedtuple

from keras.models import load_model, Model
from keras.layers import Embedding, Dropout, Dense, Reshape, LSTM, Input, concatenate, Conv1D
from keras.optimizers import Adam

from functools import lru_cache

class AnalysedGameModel(namedtuple('AnalysedGameModel', ['env', 'type'])):
  @lru_cache(maxsize=2)
  def model(self, newmodel=False):
    if self.type == 'general':
      if os.path.isfile('modules/irwin/models/generalAnalysedGame.h5') and not newmodel:
        logging.debug("model already exists, opening from file")
        return load_model('modules/irwin/models/generalAnalysedGame.h5')
    elif self.type == 'narrow':
      if os.path.isfile('modules/irwin/models/narrowAnalysedGame.h5') and not newmodel:
        logging.debug("model already exists, opening from file")
        return load_model('modules/irwin/models/narrowAnalysedGame.h5')
    logging.debug('model does not exist, building from scratch')
    pvInput = Input(shape=(None, 10), dtype='float32', name='pv_input')
    moveStatsInput = Input(shape=(None, 8), dtype='float32', name='move_input')

    advInput = Input(shape=(None,), dtype='int32', name='advantage_input')
    ranksInput = Input(shape=(None,), dtype='int32', name='ranks_input')
    moveNumberInput = Input(shape=(None,), dtype='int32', name='move_number_input')
    ambiguityInput = Input(shape=(None,), dtype='int32', name='ambiguity_input')

    # Embed rank and move number
    a1 = Embedding(input_dim=42, output_dim=32)(advInput)
    r1 = Embedding(input_dim=17, output_dim=32)(ranksInput)
    mn1 = Embedding(input_dim=62, output_dim=32)(moveNumberInput)
    am1 = Embedding(input_dim=7, output_dim=32)(ambiguityInput)

    # Merge embeddings
    mnr1 = concatenate([r1, mn1, a1, am1])
    mnr2 = Reshape((-1, 128))(mnr1)

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

    c1 = Conv1D(filters=128, kernel_size=5, name='conv1')(mvpv)

    # analyse all the moves and come to a decision about the game
    l1 = LSTM(128, return_sequences=True)(c1)
    l2 = LSTM(128, return_sequences=True, activation='sigmoid')(l1)

    c2 = Conv1D(filters=64, kernel_size=10, name='conv2')(l2)

    l3 = LSTM(64, return_sequences=True)(c2)
    l4 = LSTM(32, return_sequences=True, activation='sigmoid', name='position_words')(l3)
    l5 = LSTM(32)(l4)
    l6 = Dense(16, activation='sigmoid', name='game_word')(l5)
    d4 = Dropout(0.3)(l6)
    l6 = Dense(1, activation='sigmoid')(d4)

    s1 = Dense(16, activation='sigmoid')(l4)
    secondaryOutput = Dense(1, activation='sigmoid', name='secondary_output')(s1)

    mainOutput = Dense(1, activation='sigmoid', name='main_output')(l6)

    model = Model(inputs=[pvInput, moveStatsInput, moveNumberInput, ranksInput, advInput, ambiguityInput], outputs=[mainOutput, secondaryOutput])

    model.compile(optimizer=Adam(lr=0.0001),
      loss='binary_crossentropy',
      loss_weights=[1., 0.3],
      metrics=['accuracy'])
    return model

  @lru_cache(maxsize=1)
  def intermediateModel(self):
    baseModel = self.model() 
    model = Model(inputs=baseModel.input, outputs=[baseModel.get_layer('position_words').output, baseModel.get_layer('game_word').output])
    return model

  def train(self, epochs, newmodel=False):
    # get player sample
    logging.debug("getting model")
    model = self.model(newmodel)
    logging.debug("getting dataset")
    batch = self.getTrainingDataset()

    logging.debug("training")
    logging.debug("Batch Info: Games: " + str(len(batch['data'][0])))

    logging.debug("Game Len: " + str(len(batch['data'][2][0])))

    model.fit(batch['data'], batch['labels'], epochs=epochs, batch_size=32, validation_split=0.2)

    self.saveModel(model)
    logging.debug("complete")

  def saveModel(self, model):
    logging.debug("saving model")
    if self.type == 'general':
      model.save('modules/irwin/models/generalAnalysedGame.h5')
    if self.type == 'narrow':
      model.save('modules/irwin/models/narrowAnalysedGame.h5')

  def getTrainingDataset(self):
    logging.debug("gettings game IDs from DB")
    if self.type == 'general':
      cheatPivotEntries = self.env.gameAnalysisPlayerPivotDB.byEngine(True)
      legitPivotEntries = self.env.gameAnalysisPlayerPivotDB.byEngine(False)
    else:
      cheatPivotEntries = self.env.confidentGameAnalysisPivotDB.byEngineAndPrediction(True, 70)
      legitPivotEntries = self.env.confidentGameAnalysisPivotDB.byEngineAndPrediction(False, 70)

    logging.debug("got: "+str(len(cheatPivotEntries + legitPivotEntries)))

    shuffle(cheatPivotEntries)
    shuffle(legitPivotEntries)

    minEntries = min(len(cheatPivotEntries), len(legitPivotEntries))

    logging.debug("Getting game analyses from DB")

    cheatGameAnalyses = self.env.gameAnalysisDB.byIds([cpe.id for cpe in cheatPivotEntries])
    legitGameAnalyses = self.env.gameAnalysisDB.byIds([lpe.id for lpe in legitPivotEntries])

    logging.debug("building moveAnalysisTensors")
    cheatGameTensors = [tga.moveAnalysisTensors() for tga in cheatGameAnalyses if tga.gameLength() <= 50]
    legitGameTensors = [tga.moveAnalysisTensors() for tga in legitGameAnalyses if tga.gameLength() <= 50]

    logging.debug("batching tensors")
    return self.createBatchAndLabels(cheatGameTensors, legitGameTensors)

  @staticmethod
  def createBatchAndLabels(cheatBatch, legitBatch):
    # group the dataset into batches by the length of the dataset, because numpy needs it that way
    mlen = min(len(cheatBatch), len(legitBatch))

    cheats = cheatBatch[:mlen]
    legits = legitBatch[:mlen]

    logging.debug("batch size " + str(len(cheats + legits)))

    labels = [True]*len(cheats) + [False]*len(legits)

    blz = list(zip(cheats+legits, labels))
    shuffle(blz)

    pvs =         np.array([[m[0] for m in t] for t, l in blz])
    moveStats =   np.array([[m[1] for m in t] for t, l in blz])
    moveNumbers = np.array([[m[2] for m in t] for t, l in blz])
    ranks =       np.array([[m[3] for m in t] for t, l in blz])
    advs =        np.array([[m[4] for m in t] for t, l in blz])
    ambs =        np.array([[m[5] for m in t] for t, l in blz])

    return {
      'data': [pvs, moveStats, moveNumbers, ranks, advs, ambs],
      'labels': [
        np.array([int(l) for t, l in blz]), 
        np.array([[[int(l)]]*(len(moveStats[0])-13) for t, l in blz])
      ]
    }