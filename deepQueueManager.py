"""Deep Queue manager. Gets next item in DeepPlayerQueue, analyses the player deeply and posts result"""
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
from modules.core.GameAnalysis import GameAnalysis
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

env = Env(config)

while True:
    deepPlayerQueue = env.deepPlayerQueueDB.nextUnprocessed()
    if deepPlayerQueue is None:
        # no entries in the queue. sleep and wait for line to fill
        sleep(30)
        continue
    logging.info("Deep Queue: " + str(deepPlayerQueue))
    userId = deepPlayerQueue.id
    playerData = env.api.getPlayerData(userId)

    if playerData is None:
        logging.warning("getPlayerData returned None")
        continue

    env.playerDB.write(Player.fromPlayerData(playerData))

    # pull what we already have on the player
    gameAnalysisStore = GameAnalysisStore.new()
    gameAnalysisStore.addGames(env.gameDB.byUserId(userId))
    gameAnalysisStore.addGameAnalyses(env.gameAnalysisDB.byUserId(userId))

    # Filter games and assessments for relevant info
    try:
        gameAnalysisStore.addGames(Game.fromPlayerData(playerData))
    except KeyError:
        logging.warning("KeyError warning when adding games to analysisStore")
        continue # if this doesn't gather any useful data, skip

    env.gameDB.lazyWriteGames(gameAnalysisStore.games)

    logging.info("Already Analysed: " + str(len(gameAnalysisStore.gameAnalyses)))

    # decide which games should be analysed
    gameTensors = gameAnalysisStore.gameTensorsWithoutAnalysis(userId)
    gamesToAnalyse = []

    if gameTensors is not None:
        gamePredictions = env.irwin.predictBasicGames(gameTensors) # [(gameId, prediction)]
        if gamePredictions is None:
            logging.warning("gamePredictions is None")
        else:
            gamePredictions.sort(key=lambda tup: -tup[1])
            gids = [gid for gid, _ in gamePredictions][:5]
            gamesFromPredictions = [gameAnalysisStore.gameById(gid) for gid in gids]
            gamesFromPredictions = [g for g in gamesFromPredictions if g is not None] # just in case
            gamesToAnalyse = gamesFromPredictions + gameAnalysisStore.randomGamesWithoutAnalysis(10 - len(gids), excludeIds=gamesFromPredictions)
    
    if len(gamesToAnalyse) == 0: ## if the prior step failed
        gamesToAnalyse = gameAnalysisStore.randomGamesWithoutAnalysis()

    # analyse games with SF
    gameAnalysisStore.addGameAnalyses([
        GameAnalysis.fromGame(
            game=game,
            engine=env.engine,
            infoHandler=env.infoHandler,
            white=game.white == userId,
            nodes=env.settings['stockfish']['nodes'],
            positionAnalysisDB=env.positionAnalysisDB) for game in gamesToAnalyse])

    env.gameAnalysisDB.lazyWriteGameAnalyses(gameAnalysisStore.gameAnalyses)

    logging.info('Posting report for ' + userId)
    env.api.postReport(env.irwin.report(userId, gameAnalysisStore))
    env.restartEngine()
