import argparse
import logging
import numpy as np
import matplotlib.pyplot as plt
import json

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

legitMoveTensors = []
legitChunkTensors = []
engineMoveTensors = []
engineChunkTensors = []
for legit in legits:
  legitMoveTensors.extend(legit.tensorInputMoves())
  legitChunkTensors.extend(legit.tensorInputChunks())

for engine in engines:
  engineMoveTensors.extend(engine.tensorInputMoves())
  engineChunkTensors.extend(engine.tensorInputChunks())

plt.hist(legitMoveTensors, bins=np.arange(0,100,2))
plt.title('Move assessment frequency (Legits)')
plt.show()

plt.hist(engineMoveTensors, bins=np.arange(0,100,2))
plt.title('Move assessment frequency (Engines)')
plt.show()

plt.hist(legitChunkTensors, bins=np.arange(0,100,2))
plt.title('Chunk assessment frequency (Legits)')
plt.show()

plt.hist(engineChunkTensors, bins=np.arange(0,100,2))
plt.title('Chunk assessment frequency (Engines)')
plt.show()