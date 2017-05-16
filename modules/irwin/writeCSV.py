import csv
from random import shuffle

def writeClassifiedMovesCSV(entries):
  with open('data/classified-moves.csv', 'w') as fh:
    writer = csv.writer(fh, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['engine', 'moveNumber', 'rank', 'loss', 'advantage', 'ambiguity', 'timeConsistent', 'emt', 'onlyMove'])
    shuffle(entries)
    [writer.writerow(entry) for entry in entries]     

def writeClassifiedMoveChunksCSV(entries):
  with open('data/classified-move-chunks.csv', 'w') as fh:
    writer = csv.writer(fh, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['engine',
      'rank1', 'loss1', 'advantage1', 'ambiguity1', 'timeConsistent1', 'emt1', 'onlyMove1',
      'rank2', 'loss2', 'advantage2', 'ambiguity2', 'timeConsistent2', 'emt2', 'onlyMove2',
      'rank3', 'loss3', 'advantage3', 'ambiguity3', 'timeConsistent3', 'emt3', 'onlyMove3',
      'rank4', 'loss4', 'advantage4', 'ambiguity4', 'timeConsistent4', 'emt4', 'onlyMove4',
      'rank5', 'loss5', 'advantage5', 'ambiguity5', 'timeConsistent5', 'emt5', 'onlyMove5',
      'rank6', 'loss6', 'advantage6', 'ambiguity6', 'timeConsistent6', 'emt6', 'onlyMove6',
      'rank7', 'loss7', 'advantage7', 'ambiguity7', 'timeConsistent7', 'emt7', 'onlyMove7',
      'rank8', 'loss8', 'advantage8', 'ambiguity8', 'timeConsistent8', 'emt8', 'onlyMove8',
      'rank9', 'loss9', 'advantage9', 'ambiguity9', 'timeConsistent9', 'emt9', 'onlyMove9',
      'rank10', 'loss10', 'advantage10', 'ambiguity10', 'timeConsistent10', 'emt10', 'onlyMove10'
    ])
    shuffle(entries)
    [writer.writerow(entry) for entry in entries]

def writeClassifiedPVsCSV(entries):
  with open('data/classified-pvs.csv', 'w') as fh:
    writer = csv.writer(fh, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['engine', 'amb1', 'amb2', 'amb3', 'amb4', 'amb5'])
    shuffle(entries)
    [writer.writerow(entry) for entry in entries]

def writeClassifiedPVsDrawishCSV(entries):
  with open('data/classified-pvs-drawish.csv', 'w') as fh:
    writer = csv.writer(fh, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['engine', 'T1', 'T2', 'T3', 'T4', 'T5'])
    shuffle(entries)
    [writer.writerow(entry) for entry in entries]

def writeClassifiedPVsLosingCSV(entries):
  with open('data/classified-pvs-losing.csv', 'w') as fh:
    writer = csv.writer(fh, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['engine', 'T1', 'T2', 'T3', 'T4', 'T5'])
    shuffle(entries)
    [writer.writerow(entry) for entry in entries]

def writeClassifiedPVsOverallCSV(entries):
  with open('data/classified-pvs-overall.csv', 'w') as fh:
    writer = csv.writer(fh, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['engine', 'PV', 'PVDraw', 'PVLosing'])
    shuffle(entries)
    [writer.writerow(entry) for entry in entries]

def writeClassifiedOverallAssessmentCSV(entries):
  with open('data/classified-overall-assessment.csv', 'w') as fh:
    writer = csv.writer(fh, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['engine', 'ANOA', 'PV'])
    shuffle(entries)
    [writer.writerow(entry) for entry in entries]