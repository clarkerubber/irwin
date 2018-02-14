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

while True:
    basicPlayerQueue = env.basicPlayerQueueDB.nextUnprocessed()
    if basicPlayerQueue is not None:
        logging.info("Basic Queue: " + str(basicPlayerQueue))
        userId = basicPlayerQueue.id
        origin = basicPlayerQueue.origin
    else:
        logging.info("Basic Queue empty. Pausing")
        sleep(10)
        continue

    if env.deepPlayerQueueDB.exists(userId):
        continue
    
    gameAnalysisStore = GameAnalysisStore.new()
    gameAnalysisStore.addGames(env.gameDB.byUserIdAnalysed(userId))
    gameTensors = gameAnalysisStore.gameTensors(userId)
    if len(gameTensors) > 0:
        gamePredictions = env.irwin.predictBasicGames(gameTensors)
        deepPlayerQueue = DeepPlayerQueue.new(
            userId=userId,
            origin=origin,
            gamePredictions=gamePredictions)
        logging.info("Writing DeepPlayerQueue: " + str(deepPlayerQueue))
        env.deepPlayerQueueDB.write(deepPlayerQueue)
    else:
        logging.info("No gameTensors")