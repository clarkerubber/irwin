"""Main interface for Irwin"""

import argparse
import sys
import logging
import json

from modules.game.GameAnalysisStore import GameAnalysisStore

from utils.updatePlayerDatabase import updatePlayerDatabase
from utils.buildPositionAnalysisTable import buildPositionAnalysisTable
from utils.buildAverageReport import buildAverageReport

from Env import Env

config = {}
with open('conf/config.json') as confFile:
    config = json.load(confFile)
if config == {}:
    raise Exception('Config file empty or does not exist!')

parser = argparse.ArgumentParser(description=__doc__)
## Training
parser.add_argument("--trainbasic", dest="trainbasic", nargs="?",
                    default=False, const=True, help="train basic game model")
parser.add_argument("--trainanalysed", dest="trainanalysed", nargs="?",
                    default=False, const=True, help="train analysed game model")
parser.add_argument("--filtered", dest="filtered", nargs="?",
                    default=False, const=True, help="use filtered dataset for training")
parser.add_argument("--newmodel", dest="newmodel", nargs="?",
                    default=False, const=True, help="throw out current model. build new")

## Database building
parser.add_argument("--buildbasictable", dest="buildbasictable", nargs="?",
                    default=False, const=True,
                    help="build table of basic game activations")
parser.add_argument("--buildanalysedtable", dest="buildanalysedtable", nargs="?",
                    default=False, const=True,
                    help="build table of analysed game activations")
parser.add_argument("--buildpositiontable", dest="buildpositiontable", nargs="?",
                    default=False, const=True,
                    help="build table of analysed positions")
parser.add_argument("--updatedatabase", dest="updatedatabase", nargs="?",
                    default=False, const=True,
                    help="collect game analyses for players. Build database collection")
parser.add_argument("--buildaveragereport", dest="buildaveragereport", nargs="?",
                    default=False, const=True,
                    help="build an average report for all players in the database")

## Evaluation and testing
parser.add_argument("--eval", dest="eval", nargs="?",
                    default=False, const=True,
                    help="evaluate the performance of neural networks")
parser.add_argument("--test", dest="test", nargs="?",
                    default=False, const=True, help="test on a single player")
parser.add_argument("--discover", dest="discover", nargs="?",
                    default=False, const=True,
                    help="search for cheaters in the database that haven't been marked")

parser.add_argument("--quiet", dest="loglevel",
                    default=logging.DEBUG, action="store_const", const=logging.INFO,
                    help="reduce the number of logged messages")
settings = parser.parse_args()

logging.basicConfig(format="%(message)s", level=settings.loglevel, stream=sys.stdout)
logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)
logging.getLogger("chess.uci").setLevel(logging.WARNING)
logging.getLogger("modules.fishnet.fishnet").setLevel(logging.INFO)

env = Env(config)

if settings.updatedatabase:
    updatePlayerDatabase()

# train on a single batch
if settings.trainbasic:
    env.irwin.basicGameModel.train(
        config['irwin']['train']['epochs'],
        settings.filtered,
        settings.newmodel)

if settings.buildbasictable:
    env.irwin.buildBasicTable()

if settings.buildanalysedtable:
    env.irwin.buildAnalysedTable()

if settings.buildpositiontable:
    buildPositionAnalysisTable(env)

if settings.trainanalysed:
    env.irwin.analysedGameModel.train(
        config['irwin']['train']['epochs'],
        settings.filtered, settings.newmodel)

# test on a single user in the DB
if settings.test:
    for userId in ['chess-network', 'clarkey', 'thibault', 'uyfadcrack']:
        gameAnalysisStore = GameAnalysisStore.new()
        gameAnalysisStore.addGames(env.gameDB.byUserIdAnalysed(userId))
        gameAnalysisStore.addGameAnalyses(env.gameAnalysisDB.byUserId(userId))
        env.api.postReport(env.irwin.report(userId, gameAnalysisStore))
        logging.debug("posted")

# how good is the network?
if settings.eval:
    env.irwin.evaluate()

if settings.discover:
    env.irwin.discover()

if settings.buildaveragereport:
    buildAverageReport(env)