import argparse
import logging
import numpy as np
import matplotlib.pyplot as plt
import json
import csv

from Env import Env

config = {}
with open('conf/config.json') as confFile:
  config = json.load(confFile)
if config == {}:
  raise Exception('Config file empty or does not exist!')

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--learner", dest="learn", nargs="?",
                    default=False, const=True, help="does this bot learn")
parser.add_argument("--quiet", dest="loglevel",
                    default=logging.DEBUG, action="store_const", const=logging.INFO,
                    help="substantially reduce the number of logged messages")
settings = parser.parse_args()

config['irwin']['learn'] = settings.learn

env = Env(config)

legits = env.playerAnalysisDB.legits()
engines = env.playerAnalysisDB.engines()

def writeMoves(entries):
  with open('data/move-assessments-by-player.csv', 'w') as fh:
    writer = csv.writer(fh, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    [writer.writerow(entry) for entry in entries if len(entry) > 1]

def writeChunks(entries):
  with open('data/chunk-assessments-by-player.csv', 'w') as fh:
    writer = csv.writer(fh, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    [writer.writerow(entry) for entry in entries if len(entry) > 1]

moveActivations = []
chunkActivations = []
for legit in legits:
  moveActivations.append([0] + legit.moveActivations())
  chunkActivations.append([0] + legit.chunkActivations())

for engine in engines:
  moveActivations.append([1] + engine.moveActivations())
  chunkActivations.append([1] + engine.chunkActivations())

writeMoves(moveActivations)
writeChunks(chunkActivations)