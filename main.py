import argparse
import sys
import logging
import json
import threading
import copy
import time

from pprint import pprint

from modules.core.GameAnalysisStore import GameAnalysisStore
from modules.core.PlayerEngineStatusBus import PlayerEngineStatusBus

from Env import Env
from RequestAnalyseReportThread import RequestAnalyseReportThread
from GatherDataThread import GatherDataThread

config = {}
with open('conf/config.json') as confFile:
  config = json.load(confFile)
if config == {}:
  raise Exception('Config file empty or does not exist!')

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--trainbinary", dest="trainbinary", nargs="?",
                    default=False, const=True, help="train binary game model")
parser.add_argument("--trainbinaryforever", dest="trainbinaryforever", nargs="?",
                    default=False, const=True, help="train binary model forever")
parser.add_argument("--traintrinary", dest="traintrinary", nargs="?",
                    default=False, const=True, help="train trinary game model")
parser.add_argument("--traintrinaryforever", dest="traintrinaryforever", nargs="?",
                    default=False, const=True, help="train trinary model forever")
parser.add_argument("--epoch", dest="epoch", nargs="?",
                    default=False, const=True, help="train from start to finish")
parser.add_argument("--epochforever", dest="epochforever", nargs="?",
                    default=False, const=True, help="train from start to finish forever")
parser.add_argument("--gather", dest="gather", nargs="?",
                    default=False, const=True, help="collect and analyse players forever to build dataset. Does not use models and does not post results")
parser.add_argument("--newmodel", dest="newmodel", nargs="?",
                    default=False, const=True, help="generate a new model for training")
parser.add_argument("--no-report", dest="noreport", nargs="?",
                    default=False, const=True, help="disable posting of player reports")
parser.add_argument("--eval", dest="eval", nargs="?",
                    default=False, const=True, help="evaluate the performance of neural networks")
parser.add_argument("--buildpivottable", dest="buildpivottable", nargs="?",
                    default=False, const=True, help="build table relating game analysis to players, game length and engine status")
parser.add_argument("--buildconfidencetable", dest="buildconfidencetable", nargs="?",
                    default=False, const=True, help="build table of game analysis that the network is confident in predicting")
parser.add_argument("--test", dest="test", nargs="?",
                    default=False, const=True, help="test on a single player")
parser.add_argument("--quiet", dest="loglevel",
                    default=logging.DEBUG, action="store_const", const=logging.INFO,
                    help="reduce the number of logged messages")
settings = parser.parse_args()

logging.basicConfig(format="%(message)s", level=settings.loglevel, stream=sys.stdout)
logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)
logging.getLogger("chess.uci").setLevel(logging.WARNING)

env = Env(config)

# start the bus to update player engine status
PlayerEngineStatusBus(env.playerDB, env.settings).start()

# test on a single user in the DB
if settings.test:
  binaryModel = env.irwin.gameModelBinary()
  trinaryModel = env.irwin.gameModelTrinary()
  for userId in ['prince_upadhyay']:
    gameAnalysisStore = GameAnalysisStore.new()
    gameAnalysisStore.addGames(env.gameDB.byUserId(userId))
    gameAnalysisStore.addGameAnalyses(env.gameAnalysisDB.byUserId(userId))

    env.api.postReport(env.irwin.report(userId, gameAnalysisStore, binaryModel, trinaryModel))
    print("posted")

if settings.epoch:
  env.irwin.buildPivotTable()
  env.irwin.trainBinary()
  env.irwin.buildConfidenceTable()
  env.irwin.trainTrinary()

while settings.epochforever:
  env.irwin.buildPivotTable()
  env.irwin.trainBinary()
  env.irwin.buildConfidenceTable()
  env.irwin.trainTrinary()

if settings.buildpivottable:
  env.irwin.buildPivotTable()

if settings.buildconfidencetable:
  env.irwin.buildConfidenceTable()

# train on a single batch
if settings.trainbinary:
  env.irwin.trainBinary(settings.newmodel)

if settings.traintrinary:
  env.irwin.trainTrinary(settings.newmodel)

# how good is the network?
if settings.eval:
  env.irwin.evaluate()

# train forever
while settings.trainbinaryforever:
  env.irwin.trainBinary(settings.newmodel)
  settings.newmodel = False

# train forever
if settings.traintrinaryforever:
  #env.irwin.buildConfidenceTable()
  while True:
    env.irwin.trainTrinary(settings.newmodel)
    settings.newmodel = False

if settings.gather:
  [GatherDataThread(x, Env(config)).start() for x in range(env.settings['core']['instances'])]

if not (settings.trainbinary or settings.eval or settings.noreport or settings.test or settings.gather):
  requestAnalyseReportThread = RequestAnalyseReportThread(env)
  requestAnalyseReportThread.start()
  while True:
    time.sleep(60)
    if not requestAnalyseReportThread.isAlive():
      requestAnalyseReportThread.start()
  # we need to make new copies of Env as the engine stored in env can't be used by two threads at once