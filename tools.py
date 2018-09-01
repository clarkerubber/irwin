"""Main interface for Irwin"""
from default_imports import *

from conf.ConfigWrapper import ConfigWrapper

import argparse
import sys
import logging
import json

from modules.game.GameStore import GameStore

from utils.updatePlayerDatabase import updatePlayerDatabase
from utils.buildAnalysedPositionTable import buildAnalysedPositionTable
from utils.buildAverageReport import buildAverageReport

from Env import Env

config = ConfigWrapper.new('conf/server_config.json')

parser = argparse.ArgumentParser(description=__doc__)
## Training
parser.add_argument("--trainbasic", dest="trainbasic", nargs="?",
                default=False, const=True, help="train basic game model")
parser.add_argument("--trainanalysed", dest="trainanalysed", nargs="?",
                default=False, const=True, help="train analysed game model")
parser.add_argument("--filtered", dest="filtered", nargs="?",
                default=False, const=True , help="use filtered dataset for training")
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
args = parser.parse_args()

logging.basicConfig(format="%(message)s", level=args.loglevel, stream=sys.stdout)
logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)
logging.getLogger("chess.uci").setLevel(logging.WARNING)
logging.getLogger("modules.fishnet.fishnet").setLevel(logging.INFO)

logging.debug(args.newmodel)
env = Env(config, newmodel=args.newmodel)

if args.updatedatabase:
    updatePlayerDatabase()

# train on a single batch
if args.trainbasic:
    env.irwin.training.basicModelTraining.train(
        config['irwin model basic training epochs'],
        args.filtered)

if args.buildbasictable:
    env.irwin.training.basicModelTraining.buildTable()

if args.buildanalysedtable:
    env.irwin.training.analysedModelTraining.buildTable()

if args.buildpositiontable:
    buildAnalysedPositionTable(env)

if args.trainanalysed:
    env.irwin.training.analysedModelTraining.train(
        config['irwin model analysed training epochs'],
        args.filtered)

# test on a single user in the DB
if args.test:
    for userId in ['ralph27_velasco']:
        player = env.playerDB.byPlayerId(userId)
        gameStore = GameStore.new()
        gameStore.addGames(env.gameDB.byPlayerIdAndAnalysed(userId))
        gameStore.addAnalysedGames(env.analysedGameDB.byPlayerId(userId))
        env.api.postReport(env.irwin.report(player, gameStore))
        logging.debug("posted")

# how good is the network?
if args.eval:
    env.irwin.evaluation.evaluate()

if args.discover:
    env.irwin.discover()

if args.buildaveragereport:
    buildAverageReport(env)