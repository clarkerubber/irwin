from collections import namedtuple
from pprint import pprint
from random import shuffle

import logging
import numpy as np
import os.path

from modules.irwin.ConfidentGameAnalysisPivot import ConfidentGameAnalysisPivot
from modules.irwin.TrainingStats import TrainingStats, Accuracy, Sample
from modules.irwin.FalseReports import FalseReport

from keras.models import load_model, Model
from keras.layers import Embedding, Dropout, Dense, Reshape, LSTM, Input, concatenate, Conv1D
from keras.optimizers import Adam


class Irwin(namedtuple('Irwin', ['env', 'config'])):
  def gameModelBinary(self, newmodel=False):
    if os.path.isfile('modules/irwin/models/gameBinary.h5') and not newmodel:
      print("model already exists, opening from file")
      return load_model('modules/irwin/models/gameBinary.h5')
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

  def gameModelTrinary(self, newmodel=False):
    if os.path.isfile('modules/irwin/models/gameTrinary.h5') and not newmodel:
      print("model already exists, opening from file")
      return load_model('modules/irwin/models/gameTrinary.h5')
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
    l6 = Dense(16)(d4)

    mainOutput = Dense(3, activation='softmax', name='main_output')(l6)

    model = Model(inputs=[pvInput, moveStatsInput, moveNumberInput, ranksInput, advInput, ambiguityInput], outputs=[mainOutput])

    model.compile(optimizer=Adam(lr=0.0001),
      loss='categorical_crossentropy',
      metrics=['accuracy'])
    return model

  def trainBinary(self, newmodel=False):
    # get player sample
    print("getting model")
    model = self.gameModelBinary(newmodel)
    print("getting dataset")
    batches = self.getBinaryTrainingDataset(self.config['train']['batchSize'])

    print("training")
    for x in range(2):
      for b in batches:
        print("Batch Info: Games: " + str(len(b['batch'][0])))
        print("Game Len: " + str(len(b['batch'][2][0])))
        model.fit(b['batch'], b['labels'], epochs=self.config['train']['cycles'], batch_size=32, validation_split=0.2)
        self.saveBinaryGameModel(model)
      shuffle(batches)
    print("complete")

  def trainTrinary(self, newmodel=False):
    # get player sample
    print("getting model")
    model = self.gameModelTrinary(newmodel)
    print("getting dataset")
    batches = self.getTrinaryTrainingDataset(self.config['train']['batchSize'])

    print("training")
    for x in range(2):
      for b in batches:
        print("Batch Info: Games: " + str(len(b['batch'][0])))
        print("Game Len: " + str(len(b['batch'][2][0])))
        model.fit(b['batch'], b['labels'], epochs=self.config['train']['cycles'], batch_size=32, validation_split=0.2)
        self.saveTrinaryGameModel(model)
      shuffle(batches)
    print("complete")

  def saveBinaryGameModel(self, model):
    print("saving model")
    model.save('modules/irwin/models/gameBinary.h5')

  def saveTrinaryGameModel(self, model):
    print("saving model")
    model.save('modules/irwin/models/gameTrinary.h5')

  def getBinaryTrainingDataset(self, batchSize):
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
      sampleSize = min(int(batchSize/2), minEntries)

      cheatGameAnalyses.extend(self.env.gameAnalysisDB.byIds([cpe.id for cpe in cheatPivotEntries[:sampleSize]]))
      legitGameAnalyses.extend(self.env.gameAnalysisDB.byIds([lpe.id for lpe in legitPivotEntries[:sampleSize]]))

    print("getting moveAnalysisTensors")
    cheatGameTensors = [tga.moveAnalysisTensors() for tga in cheatGameAnalyses]
    legitGameTensors = [tga.moveAnalysisTensors() for tga in legitGameAnalyses]

    print("batching tensors")
    return Irwin.binaryCreateBatchAndLabels(cheatGameTensors, legitGameTensors)

  def getTrinaryTrainingDataset(self, batchSize):
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
      sampleSize = min(int(batchSize/2), minEntries)

      cheatGameAnalyses.extend(self.env.gameAnalysisDB.byIds([cpe.id for cpe in cheatPivotEntries[:sampleSize]]))
      legitGameAnalyses.extend(self.env.gameAnalysisDB.byIds([lpe.id for lpe in legitPivotEntries[:sampleSize]]))
      unclearGameAnalyses.extend(self.env.gameAnalysisDB.byIds([lpe.id for lpe in unclearPivotEntries[:sampleSize]]))

    print("getting moveAnalysisTensors")
    cheatGameTensors = [tga.moveAnalysisTensors() for tga in cheatGameAnalyses]
    legitGameTensors = [tga.moveAnalysisTensors() for tga in legitGameAnalyses]
    unclearGameTensors = [tga.moveAnalysisTensors() for tga in unclearGameAnalyses]

    print("batching tensors")
    return Irwin.trinaryCreateBatchAndLabels(cheatGameTensors, legitGameTensors, unclearGameTensors)

  def getEvaluationDataset(self, batchSize):
    print("getting players", end="...", flush=True)
    players = self.env.playerDB.balancedSample(batchSize)
    print(" %d" % len(players))
    print("getting game analyses")
    analysesByPlayer = [(player, [ga for ga in self.env.gameAnalysisDB.byUserId(player.id) if len(ga.moveAnalyses) < 60]) for player in players]
    return analysesByPlayer

  def evaluate(self):
    print("evaluate model")
    print("getting model")
    model = self.gameModelBinary()
    print("getting dataset")
    analysesByPlayer = self.getEvaluationDataset(self.config['evalSize'])
    activations = [Irwin.activation(self.predict([ga.moveAnalysisTensors() for ga in gameAnalyses[1]], model)) for gameAnalyses in analysesByPlayer]
    outcomes = list(zip(analysesByPlayer, [Irwin.outcome(a, 90, ap[0].engine) for ap, a in zip(analysesByPlayer, activations)]))
    tp = len([a for a in outcomes if a[1] == 1])
    fn = len([a for a in outcomes if a[1] == 2])
    tn = len([a for a in outcomes if a[1] == 3])
    fp = len([a for a in outcomes if a[1] == 4])

    fpnames = [a[0][0].id for a in outcomes if a[1] == 4]

    print("True positive: " + str(tp))
    print("False negative: " + str(fn))
    print("True negative: " + str(tn))
    print("False positive: " + str(fp))

    pprint(fpnames)

  def predict(self, tensors, binaryModel=None, trinaryModel=None):
    if binaryModel == None:
      binaryModel = self.gameModelBinary()

    if trinaryModel == None:
      trinaryModel = self.gameModelTrinary()

    pvs =         [[m[0] for m in p][:40] for p in tensors]
    moveStats =   [[m[1] for m in p][:40] for p in tensors]
    moveNumbers = [[m[2] for m in p][:40] for p in tensors]
    ranks =       [[m[3] for m in p][:40] for p in tensors]
    advs =        [[m[4] for m in p][:40] for p in tensors]
    ambs =        [[m[5] for m in p][:40] for p in tensors]

    binaryPredictions = []
    trinaryPredictions = []
    for p, m, mn, r, a, am in zip(pvs, moveStats, moveNumbers, ranks, advs, ambs):
      binaryPredictions.append(binaryModel.predict([np.array([p]), np.array([m]), np.array([mn]), np.array([r]), np.array([a]), np.array([am])]))
      trinaryPredictions.append(trinaryModel.predict([np.array([p]), np.array([m]), np.array([mn]), np.array([r]), np.array([a]), np.array([am])]))

    return list(zip(binaryPredictions, trinaryPredictions))

  def report(self, userId, gameAnalysisStore, binaryModel=None, trinaryModel=None):
    predictions = self.predict(gameAnalysisStore.gameAnalysisTensors(), binaryModel, trinaryModel)
    report = {
      'userId': userId,
      'activation': Irwin.activation(predictions),
      'games': [Irwin.gameReport(ga, p) for ga, p in zip(gameAnalysisStore.gameAnalyses, predictions)]
    }
    return report

  def buildPivotTable(self):
    return True #stub

  def buildConfidenceTable(self):
    cheatGameAnalyses = []
    legitGameAnalyses = []
    for length in range(20, 60):
      print("getting games of length: " + str(length))
      cheatPivotEntries = self.env.gameAnalysisPlayerPivotDB.byEngineAndLength(True, length)
      legitPivotEntries = self.env.gameAnalysisPlayerPivotDB.byEngineAndLength(False, length)

      cheatGameAnalyses.extend(self.env.gameAnalysisDB.byIds([cpe.id for cpe in cheatPivotEntries]))
      legitGameAnalyses.extend(self.env.gameAnalysisDB.byIds([lpe.id for lpe in legitPivotEntries]))

    model = self.gameModelBinary()

    print("getting moveAnalysisTensors")
    cheatTensors = [tga.moveAnalysisTensors() for tga in cheatGameAnalyses]
    legitTensors = [tga.moveAnalysisTensors() for tga in legitGameAnalyses]

    print("predicting the things")
    cheatGamePredictions = self.predict(cheatTensors, model)
    legitGamePredictions = self.predict(legitTensors, model)

    confidentCheats = [ConfidentGameAnalysisPivot.fromGamesAnalysisandPrediction(gameAnalysis, prediction[0], engine=True) for gameAnalysis, prediction in zip(cheatGameAnalyses, cheatGamePredictions)]
    confidentLegits = [ConfidentGameAnalysisPivot.fromGamesAnalysisandPrediction(gameAnalysis, prediction[0], engine=False) for gameAnalysis, prediction in zip(legitGameAnalyses, legitGamePredictions)]

    print("writing to db")
    self.env.confidentGameAnalysisPivotDB.lazyWriteMany(confidentCheats + confidentLegits)

  @staticmethod
  def outcome(a, t, e): # activation, threshold, expected value
    if a > t and e:
      return 1 # true positive
    if a <= t and e:
      return 2 # false negative
    if a <= t and not e:
      return 3 # true negative
    else:
      return 4 # false positive

  @staticmethod
  def activation(predictions): # this is a weighted average. 90+ -> 10x, 80+ -> 5x, 70+ -> 3x, 60+ -> 2x, 50- -> 1x
    ps = Irwin.flatten([Irwin.activationWeight(binaryPrediction[0][0][0])*[binaryPrediction[0][0][0]] for binaryPrediction, trinaryPrediction in predictions if trinaryPrediction[0][2] < 0.3]) # multiply entry amount by weight
    if len(ps) == 0:
      return 0
    return int(100*sum(ps)/len(ps))

  @staticmethod
  def activationWeight(v):
    if v > 0.90:
      return 10
    if v > 0.80:
      return 5
    if v > 0.70:
      return 3
    if v > 0.60:
      return 2
    return 1

  @staticmethod
  def gameReport(gameAnalysis, prediction):
    return {
      'gameId': gameAnalysis.gameId,
      'activation': int(100*prediction[1][0][0]), # [*binary* | ternary][*game* | moves][*batch zero score*]
      'moves': [Irwin.moveReport(am, p) for am, p in zip(gameAnalysis.moveAnalyses, list(prediction[0][1][0]))]
    }

  @staticmethod
  def moveReport(analysedMove, prediction):
    return {
      'a': int(100*prediction[0]),
      'r': analysedMove.trueRank(),
      'm': analysedMove.ambiguity(),
      'o': int(100*analysedMove.advantage()),
      'l': int(100*analysedMove.winningChancesLoss())
    }

  @staticmethod
  def getGameEngineStatus(gameAnalysis, players):
    return any([p for p in players if gameAnalysis.userId == p.id and p.engine])

  @staticmethod
  def assignLabels(gameAnalyses, players):
    return [int(Irwin.getGameEngineStatus(gameAnalysis, players)) for gameAnalysis in gameAnalyses]

  @staticmethod
  def binaryCreateBatchAndLabels(cheatBatch, legitBatch):
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
      if len(cheats + legits) > 64:
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

  @staticmethod
  def trinaryCreateBatchAndLabels(cheatBatch, legitBatch, unclearBatch):
    batches = []
    # group the dataset into batches by the length of the dataset, because numpy needs it that way
    for x in range(20, 60):
      cheats = list([r for r in cheatBatch if len(r) == x])
      legits = list([r for r in legitBatch if len(r) == x])
      unclears = list([r for r in unclearBatch if len(r) == x])

      mlen = min(len(cheats), len(legits), len(unclears))

      cheats = cheats[:mlen]
      legits = legits[:mlen]
      unclears = unclears[:mlen]

      cl = [[1, 0, 0]]*len(cheats) + [[0, 1, 0]]*len(legits) + [[0, 0, 1]]*len(unclears)

      blz = list(zip(cheats+legits+unclears, cl))
      shuffle(blz)

      # only make the batch trainable if it's big
      if len(cheats + legits + unclears) > 64:
        pvs =         np.array([[m[0] for m in p[0]] for p in blz])
        moveStats =   np.array([[m[1] for m in p[0]] for p in blz])
        moveNumbers = np.array([[m[2] for m in p[0]] for p in blz])
        ranks =       np.array([[m[3] for m in p[0]] for p in blz])
        advs =        np.array([[m[4] for m in p[0]] for p in blz])
        ambs =        np.array([[m[5] for m in p[0]] for p in blz])

        batches.append({
          'batch': [pvs, moveStats, moveNumbers, ranks, advs, ambs],
          'labels': np.array([i[1] for i in blz])
        })
    shuffle(batches)
    return batches

  @staticmethod
  def flatten(l):
    return [item for sublist in l for item in sublist]