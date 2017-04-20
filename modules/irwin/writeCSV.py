import csv
from random import shuffle

def writeClassifiedMovesCSV(entries):
  with open('data/classified-moves.csv', 'w') as fh:
    writer = csv.writer(fh, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['engine', 'titled', 'moveNumber', 'rank', 'loss', 'advantage', 'ambiguity', 'timeConsistent', 'bot', 'blur'])
    shuffle(entries)
    [writer.writerow(entry) for entry in entries]
      

def writeClassifiedMoveChunksCSV(entries):
  with open('data/classified-move-chunks.csv', 'w') as fh:
    writer = csv.writer(fh, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['engine', 'titled', 'bot', 'blurs',
      'rank1', 'loss1', 'advantage1', 'ambiguity1', 'timeConsistent1'
      'rank2', 'loss2', 'advantage2', 'ambiguity2', 'timeConsistent2'
      'rank3', 'loss3', 'advantage3', 'ambiguity3', 'timeConsistent3'
      'rank4', 'loss4', 'advantage4', 'ambiguity4', 'timeConsistent4'
      'rank5', 'loss5', 'advantage5', 'ambiguity5', 'timeConsistent5'
      'rank6', 'loss6', 'advantage6', 'ambiguity6', 'timeConsistent6'
      'rank7', 'loss7', 'advantage7', 'ambiguity7', 'timeConsistent7'
      'rank8', 'loss8', 'advantage8', 'ambiguity8', 'timeConsistent8'
      'rank9', 'loss9', 'advantage9', 'ambiguity9', 'timeConsistent9'
      'rank10', 'loss10', 'advantage10', 'ambiguity10', 'timeConsistent10'
    ])
    shuffle(entries)
    [writer.writerow(entry) for entry in entries]
      