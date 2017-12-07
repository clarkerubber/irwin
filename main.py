import argparse
import sys
import logging
import json
import threading
import copy

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
parser.add_argument("--train", dest="train", nargs="?",
                    default=False, const=True, help="force training to start")
parser.add_argument("--trainforever", dest="trainforever", nargs="?",
                    default=False, const=True, help="train forever")
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
  for userId in ['thibault']:
    gameAnalysisStore = GameAnalysisStore.new()
    gameAnalysisStore.addGames(env.gameDB.byUserId(userId))
    gameAnalysisStore.addGameAnalyses(env.gameAnalysisDB.byUserId(userId))

    env.api.postReport(env.irwin.report(userId, gameAnalysisStore))
    print("posted")

if settings.buildpivottable:
  env.irwin.buildPivotTable()

if settings.buildconfidencetable:
  env.irwin.buildConfidenceTable()

# train on a single batch
if settings.train:
  env.irwin.train(settings.newmodel)

# how good is the network?
if settings.eval:
  env.irwin.evaluate()

# train forever
while settings.trainforever:
  env.irwin.buildConfidenceTable()
  env.irwin.train(settings.newmodel)
  settings.newmodel = False

if settings.gather:
  [GatherDataThread(x, Env(config)).start() for x in range(env.settings['core']['instances'])]

if not (settings.train or settings.eval or settings.noreport or settings.test or settings.gather):
  [RequestAnalyseReportThread(x, Env(config)).start() for x in range(env.settings['core']['instances'])] 
  # we need to make new copies of Env as the engine stored in env can't be used by two threads at once