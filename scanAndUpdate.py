"""Basic Queue manager. Gets next item in BasicPlayerQueue and creates entry for DeepPlayerQueue"""
import argparse
import logging
import json
import sys
from time import sleep

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

def updatePlayerData(env, userId):
    playerData = env.api.getPlayerData(userId)
    if playerData is None:
        logging.warning("getPlayerData returned None for " + userId)
        return

    player = Player.fromPlayerData(playerData)
    env.playerDB.write(player)
    env.gameDB.lazyWriteGames(Game.fromPlayerData(playerData))

def calcWriteDeepQueue(userId, origin='random'):
    updatePlayerData(env, userId)
    if player.engine and origin != 'moderator':
        logging.info(userId + " is now an engine. Removing all jobs")
        env.deepPlayerQueueDB.removeUserId(userId)
        return

    gameAnalysisStore = GameAnalysisStore.new()
    gameAnalysisStore.addGames(env.gameDB.byUserIdAnalysed(userId))
    gameTensors = gameAnalysisStore.gameTensors(userId)
    if len(gameTensors) > 0:
        gamePredictions = env.irwin.predictBasicGames(gameTensors)
        deepPlayerQueue = DeepPlayerQueue.new(
            userId=userId,
            origin=origin,
            gamePredictions=gamePredictions)
        if origin == 'random' and deepPlayerQueue.precedence < 80:
            return # not worth performing spot check
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
    sleep(2)
    updateOldest()
    spotCheck()