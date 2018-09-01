"""Goes through the database and finds players to update with new data from lichess"""
import argparse
import logging
import json
import sys
from random import randint

from modules.queue.DeepPlayerQueue import DeepPlayerQueue

from modules.game.Player import Player
from modules.game.Game import Game
from modules.game.GameStore import GameStore

from Env import Env

parser = argparse.ArgumentParser(description=__doc__)

parser.add_argument("--quiet", dest="loglevel",
                default=logging.DEBUG, action="store_const", const=logging.INFO,
                    help="reduce the number of logged messages")
config = parser.parse_args()

logging.basicConfig(format="%(message)s", level=config.loglevel, stream=sys.stdout)
logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)
logging.getLogger("chess.uci").setLevel(logging.WARNING)
logging.getLogger("modules.fishnet.fishnet").setLevel(logging.INFO)

config = {}
with open('conf/config.json') as confFile:
    config = json.load(confFile)
if config == {}:
    raise Exception('Config file empty or does not exist!')

env = Env(config, engine=False)

def updatePlayerData(playerId):
    playerData = env.api.getPlayerData(playerId)
    if playerData is None:
        logging.warning("getPlayerData returned None for " + playerId)
        return None

    player = Player.fromPlayerData(playerData)
    env.playerDB.write(player)
    env.gameDB.writeMany(Game.fromPlayerData(playerData))

    return player

def predictPlayer(playerId):
    gameStore = GameStore.new()
    gameStore.addGames(env.gameDB.byPlayerIdAndAnalysed(playerId))
    gameTensors = gameStore.gameTensors(playerId)

    if len(gameTensors) > 0:
        return env.irwin.predictBasicGames(gameTensors)
    return None

def updateOldestPlayerQueue():
    logging.info("--Updating Oldest DeepPlayerQueue--")
    deepPlayerQueue = env.deepPlayerQueueDB.oldest()
    logging.info("Source: " + str(deepPlayerQueue))

    if deepPlayerQueue is not None:
        if deepPlayerQueue.owner is None:
            playerId = deepPlayerQueue.id
            player = updatePlayerData(playerId)

            if player is None:
                logging.info("No player data")
                return

            if player.engine:
                logging.info("Player is now engine. Closing all reports.")
                env.modReportDB.close(playerId)
                if deepPlayerQueue.origin != 'moderator':
                    logging.info("And not requested by a moderator. Closing analysis")
                    env.deepPlayerQueueDB.removePlayerId(playerId)
                    return

            predictions = predictPlayer(playerId)
            if predictions is None:
                logging.info("No predictions to process. Removing Queue Item")
                env.deepPlayerQueueDB.removePlayerId(player.id)
                return

            deepPlayerQueue = DeepPlayerQueue.new(
                playerId=playerId,
                origin=deepPlayerQueue.origin,
                gamePredictions=predictions)

            if player.reportScore is None:
                env.modReportDB.close(player.id)

            if (deepPlayerQueue.precedence > 4000
                and deepPlayerQueue.origin in ['report', 'moderator']):
                env.deepPlayerQueueDB.write(deepPlayerQueue)
            else:
                logging.info("DeepPlayerQueue is insignificant. Removing")
                env.deepPlayerQueueDB.removePlayerId(playerId)

def spotCheck():
    logging.info("--Spot check on player DB--")
    randomPlayer = env.playerDB.oldestNonEngine()
    logging.info("Player: " + str(randomPlayer))
    if randomPlayer is not None:
        playerId = randomPlayer.id
        player = updatePlayerData(playerId)

        if player is None:
            logging.info("No player data")
            return

        if player.engine and randint(0,9) != 5:
            logging.info("Diced didn't roll lucky. Player is engine. Not proceeding")
            return

        predictions = predictPlayer(playerId)

        if predictions is None:
            logging.info("No predictions to process")
            return

        deepPlayerQueue = DeepPlayerQueue.new(
            playerId=playerId,
            origin='random',
            gamePredictions=predictions)

        if deepPlayerQueue.precedence < 6000:
            logging.info("Precedence < 6000. No point checking.")
            return

        env.deepPlayerQueueDB.write(deepPlayerQueue)

def updateOldestReport():
    logging.info("--Updating Oldest Report--")
    report = env.modReportDB.oldestUnprocessed()
    logging.info("Report: " + str(report))
    if report is not None:
        playerId = report.id

        if env.deepPlayerQueueDB.owned(playerId):
            logging.info("DeepPlayerQueue object exists and has owner")
            return

        player = updatePlayerData(playerId)

        if player is None:
            logging.info("No player data")
            return

        if player.engine:
            logging.info("Player is now engine")
            env.modReportDB.close(playerId)
            return

        predictions = predictPlayer(playerId)

        if predictions is None:
            logging.info("No predictions to process")
            return

        if player.reportScore is None:
            env.modReportDB.close(player.id)
            env.deepPlayerQueueDB.removePlayerId(player.id)
        else:
            deepPlayerQueue = DeepPlayerQueue.new(
                playerId=playerId,
                origin='reportupdate',
                gamePredictions=predictions)

            env.deepPlayerQueueDB.write(deepPlayerQueue)

while True:
    updateOldestPlayerQueue()
    updateOldestReport()
    spotCheck()