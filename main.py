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
parser.add_argument("--no-report", dest="noreport", nargs="?",
                    default=False, const=True, help="disable posting of player reports")
parser.add_argument("--eval", dest="eval", nargs="?",
                    default=False, const=True, help="evaluate the performance of neural networks")
parser.add_argument("--test", dest="test", nargs="?",
                    default=False, const=True, help="test on a single player")
parser.add_argument("--quiet", dest="loglevel",
                    default=logging.DEBUG, action="store_const", const=logging.INFO,
                    help="reduce the number of logged messages")
settings = parser.parse_args()

config['irwin']['learn'] = settings.train

logging.basicConfig(format="%(message)s", level=settings.loglevel, stream=sys.stdout)
logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)
logging.getLogger("chess.uci").setLevel(logging.WARNING)

env = Env(config)

# test on a single user in the DB
if settings.test:
  userId = 'ohsusanna'
  playerData = env.api.getPlayerData(userId)
  pprint(playerData)
  gameAnalysisStore = GameAnalysisStore.new()
  gameAnalysisStore.addGames(env.gameDB.byUserId(userId))
  gameAnalysisStore.addGameAnalyses(env.gameAnalysisDB.byUserId(userId))

  env.api.postReport(env.irwin.report(userId, gameAnalysisStore))
  print("posted")

# train on a single batch
if settings.train:
  env.irwin.train()

# how good is the network?
if settings.eval:
  env.irwin.evaluate()

# train forever
while settings.trainforever:
  env.irwin.train()

# start the bus to update player engine status
PlayerEngineStatusBus(env.playerDB, env.settings).start()

if not (settings.train or settings.eval or settings.noreport or settings.test):
  [RequestAnalyseReportThread(x, Env(config)).start() for x in range(env.settings['core']['threads'])] 
  # we need to make new copies of Env as the engine stored in env can't be used by two threads at once