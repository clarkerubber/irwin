"""Basic Queue manager. Gets next item in BasicPlayerQueue and creates entry for DeepPlayerQueue"""
import argparse
import logging
import json
import sys
from random import randint

from modules.queue.DeepPlayerQueue import DeepPlayerQueue

from modules.game.Player import Player
from modules.game.Game import Game
from modules.game.GameAnalysisStore import GameAnalysisStore

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

def updatePlayerData(userId):
    playerData = env.api.getPlayerData(userId)
    if playerData is None:
        logging.warning("getPlayerData returned None for " + userId)
        return None

    player = Player.fromPlayerData(playerData)
    env.playerDB.write(player)
    env.gameDB.lazyWriteGames(Game.fromPlayerData(playerData))

    return player

def predictPlayer(userId):
    gameAnalysisStore = GameAnalysisStore.new()
    gameAnalysisStore.addGames(env.gameDB.byUserIdAnalysed(userId))
    gameTensors = gameAnalysisStore.gameTensors(userId)

    if len(gameTensors) > 0:
        return env.irwin.predictBasicGames(gameTensors)
    return None

def updateOldestPlayerQueue():
    logging.info("--Updating Oldest DeepPlayerQueue--")
    deepPlayerQueue = env.deepPlayerQueueDB.oldest()
    logging.info("Source: " + str(deepPlayerQueue))

    if deepPlayerQueue is not None:
        if deepPlayerQueue.owner is None:
            userId = deepPlayerQueue.id
            player = updatePlayerData(userId)

            if player is None:
                logging.info("No player data")
                return

            if player.engine:
                logging.info("Player is now engine. Closing all reports.")
                env.reportDB.close(userId)
                if deepPlayerQueue.origin != 'moderator':
                    logging.info("And not requested by a moderator. Closing analysis")
                    env.deepPlayerQueueDB.removeUserId(userId)
                    return

            predictions = predictPlayer(userId)
            if predictions is None:
                logging.info("No predictions to process")
                return

            deepPlayerQueue = DeepPlayerQueue.new(
                userId=userId,
                origin=deepPlayerQueue.origin,
                gamePredictions=predictions)

            if (deepPlayerQueue.precedence > 4000
                and deepPlayerQueue.origin in ['report', 'moderator']):
                env.deepPlayerQueueDB.write(deepPlayerQueue)
            else:
                logging.info("DeepPlayerQueue is insignificant. Removing")
                env.deepPlayerQueueDB.removeUserId(userId)

def spotCheck():
    logging.info("--Spot check on player DB--")
    randomPlayer = env.playerDB.oldestNonEngine()
    logging.info("Player: " + str(randomPlayer))
    if randomPlayer is not None:
        userId = randomPlayer.id
        player = updatePlayerData(userId)

        if player is None:
            logging.info("No player data")
            return

        if player.engine and randint(0,9) != 5:
            logging.info("Diced didn't roll lucky. Player is engine. Not proceeding")
            return

        predictions = predictPlayer(userId)

        if predictions is None:
            logging.info("No predictions to process")
            return

        deepPlayerQueue = DeepPlayerQueue.new(
            userId=userId,
            origin='random',
            gamePredictions=predictions)

        if deepPlayerQueue.precedence < 6000:
            logging.info("Precedence < 6000. No point checking.")

        env.deepPlayerQueueDB.write(deepPlayerQueue)

def updateOldestReport():
    logging.info("--Updating Oldest Report--")
    report = env.reportDB.oldestUnprocessed()
    logging.info("Report: " + str(report))
    if report is not None:
        userId = report.id

        if env.deepPlayerQueueDB.owned(userId):
            logging.info("DeepPlayerQueue object exists and has owner")
            return

        player = updatePlayerData(userId)

        if player is None:
            logging.info("No player data")
            return

        if player.engine:
            logging.info("Player is now engine")
            env.reportDB.close(userId)
            return

        predictions = predictPlayer(userId)

        if predictions is None:
            logging.info("No predictions to process")
            return

        deepPlayerQueue = DeepPlayerQueue.new(
            userId=userId,
            origin='reportupdate',
            gamePredictions=predictions)

        env.deepPlayerQueueDB.write(deepPlayerQueue)

while True:
    updateOldestPlayerQueue()
    updateOldestReport()
    spotCheck()