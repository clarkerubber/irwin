"""Basic Queue manager. Gets next item in BasicPlayerQueue and creates entry for DeepPlayerQueue"""
import argparse
import logging
import json
import sys
from time import sleep
from math import ceil

import numpy as np

from modules.queue.DeepPlayerQueue import DeepPlayerQueue

from modules.core.Player import Player
from modules.core.Game import Game
from modules.core.GameAnalysisStore import GameAnalysisStore

from Env import Env

parser = argparse.ArgumentParser(description=__doc__)

parser.add_argument("--quiet", dest="loglevel",
                    default=logging.DEBUG, action="store_const", const=logging.INFO,
                    help="reduce the number of logged messages")
settings = parser.parse_args()

logging.basicConfig(format="%(message)s", level=settings.loglevel, stream=sys.stdout)
logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)
logging.getLogger("chess.uci").setLevel(logging.WARNING)
logging.getLogger("modules.fishnet.fishnet").setLevel(logging.INFO)

config = {}
with open('conf/config.json') as confFile:
    config = json.load(confFile)
if config == {}:
    raise Exception('Config file empty or does not exist!')

env = Env(config, engine=False)

def calcWriteDeepQueue(userId, origin='random'):
    playerData = env.api.getPlayerData(userId)
    if playerData is None:
        logging.warning("getPlayerData returned None for " + userId)
        return

    player = Player.fromPlayerData(playerData)
    env.playerDB.write(player)
    env.gameDB.lazyWriteGames(Game.fromPlayerData(playerData))

    if player.engine and origin != 'moderator':
        logging.info(userId + " is now and engine. Removing all jobs")
        env.deepPlayerQueueDB.removeUserId(userId)
        return

    gameAnalysisStore = GameAnalysisStore.new()
    gameAnalysisStore.addGames(env.gameDB.byUserId(userId))
    gameTensors = gameAnalysisStore.gameTensors(userId)
    if len(gameTensors) > 0:
        gamePredictions = env.irwin.predictBasicGames(gameTensors)
        activations = sorted([a[1] for a in gamePredictions], reverse=True)
        top30avg = ceil(np.average(activations[:ceil(0.3*len(activations))]))
        if origin == 'report':
            originPrecedence = 50
        else:
            originPrecedence = 0
        deepPlayerQueue = DeepPlayerQueue(
            id=userId,
            origin=origin,
            owner=None,
            precedence=top30avg+originPrecedence)
        logging.info("Writing DeepPlayerQueue: " + str(deepPlayerQueue))
        env.deepPlayerQueueDB.write(deepPlayerQueue)
    else:
        logging.info("No gameTensors")

def updateOldest():
    deepPlayerQueue = env.deepPlayerQueueDB.oldest()
    if deepPlayerQueue is not None:
        if deepPlayerQueue.owner is None:
            calcWriteDeepQueue(deepPlayerQueue.id, deepPlayerQueue.origin)

def spotCheck():
    randomPlayer = env.playerDB.randomNonEngine()
    if randomPlayer is not None:
        calcWriteDeepQueue(randomPlayer.id)

while True:
    updateOldest()
    sleep(2)
    spotCheck()
    sleep(2)