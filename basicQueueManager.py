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

while True:
    basicPlayerQueue = env.basicPlayerQueueDB.nextUnprocessed()
    if basicPlayerQueue is not None:
        logging.info("Basic Queue: " + str(basicPlayerQueue))
        userId = userId
        origin = basicPlayerQueue.origin
    else:
        # no entries in the queue. occupy time by scouring the DB
        randomPlayer = env.playerDB.randomNonEngine()
        logging.info("No jobs, found random non engine: " + str(randomPlayer))
        userId = randomPlayer.id
        origin = 'random'

        # update player's data
        playerData = env.api.getPlayerData(userId)
        if playerData is None:
            logging.warning("getPlayerData returned None")
            continue

        # write data to the db
        env.playerDB.write(Player.fromPlayerData(playerData))
        env.gameDB.lazyWriteGames(Game.fromPlayerData(playerData))
    
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
        logging.info("no game tensors")