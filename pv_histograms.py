import argparse
import logging
import numpy as np
import matplotlib.pyplot as plt

from Env import Env

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("token", metavar="TOKEN",
                    help="secret token for the lichess api")
parser.add_argument("learn", metavar="LEARN",
                    help="does this bot learn", nargs="?", type=int, default=1)
parser.add_argument("threads", metavar="THREADS", nargs="?", type=int, default=4,
                    help="number of engine threads")
parser.add_argument("memory", metavar="MEMORY", nargs="?", type=int, default=2048,
                    help="memory in MB to use for engine hashtables")
parser.add_argument("--quiet", dest="loglevel",
                    default=logging.DEBUG, action="store_const", const=logging.INFO,
                    help="substantially reduce the number of logged messages")
settings = parser.parse_args()

env = Env(settings)

legits = env.playerAnalysisDB.legits()
engines = env.playerAnalysisDB.engines()

legitPVs = [[], [], [], [], []]
enginePVs = [[], [], [], [], []]
for legit in legits:
  pvs = legit.gameAnalyses.pv0ByAmbiguityStats()
  for ambiguity, freq in enumerate(pvs):
    if freq is not None:
      legitPVs[ambiguity].append(freq)

for engine in engines:
  pvs = engine.tensorInputPVs()
  for ambiguity, freq in enumerate(pvs):
    if freq is not None:
      enginePVs[ambiguity].append(freq)

for ambiguity, pvs in enumerate(legitPVs):
  plt.hist(pvs, bins=np.arange(0,100,2))
  plt.title('PV0 Rate for Ambiguity Factor '+str(ambiguity+1)+' (Legits)')
  plt.show()

for ambiguity, pvs in enumerate(enginePVs):
  plt.hist(pvs, bins=np.arange(0,100,2))
  plt.title('PV0 Rate for Ambiguity Factor '+str(ambiguity+1)+' (Engines)')
  plt.show()