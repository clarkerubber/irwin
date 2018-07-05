"""Deep Queue manager. Gets next item in DeepPlayerQueue, analyses the player deeply and posts result"""
import argparse
import logging
import json
import sys
from time import sleep

from modules.game.Player import Player
from modules.game.Game import Game
from modules.game.AnalysedGame import AnalysedGame
from modules.game.GameStore import GameStore

from Env import Env

parser = argparse.ArgumentParser(description=__doc__)

parser.add_argument("--name", dest="name",
                    default=None, type=str, help="name of the thread")
parser.add_argument("--quiet", dest="loglevel",
                    default=logging.DEBUG, action="store_const", const=logging.INFO,
                    help="reduce the number of logged messages")

settings = parser.parse_args()

logging.info("Starting: " + str(settings.name))

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
    deepPlayerQueue = env.deepPlayerQueueDB.nextUnprocessed(settings.name)
    if deepPlayerQueue is None:
        # no entries in the queue. sleep and wait for line to fill
        logging.info("No players in deepPlayerQueue to analyse. Waiting")
        sleep(30)
        continue
    logging.info("Deep Queue: " + str(deepPlayerQueue))
    userId = deepPlayerQueue.id
    playerData = env.api.getPlayerData(userId)

    if playerData is None:
        logging.warning("getPlayerData returned None")
        env.deepPlayerQueueDB.complete(deepPlayerQueue)
        continue

    # get player data, this is really only
    # useful for knowing which games must be analysed
    player = env.playerDB.byId(userId)

    # pull what we already have on the player
    gameStore = GameStore.new()
    gameStore.addGames(env.gameDB.byUserId(userId))
    gameStore.addAnalysedGames(env.analysedGameDB.byUserId(userId))

    # Filter games and assessments for relevant info
    try:
        gameStore.addGames(Game.fromPlayerData(playerData))
    except KeyError:
        logging.warning("KeyError warning when adding games to analysisStore")
        env.deepPlayerQueueDB.complete(deepPlayerQueue)
        continue # if this doesn't gather any useful data, skip

    env.gameDB.lazyWriteGames(gameStore.games)

    logging.info("Already Analysed: " + str(len(gameStore.analysedGames)))

    # decide which games should be analysed
    gameTensors = gameStore.gameTensorsWithoutAnalysis(userId)

    if len(gameTensors) > 0:
        gamePredictions = env.irwin.predictBasicGames(gameTensors) # [(gameId, prediction)]
        gamePredictions.sort(key=lambda tup: -tup[1])
        gids = [gid for gid, _ in gamePredictions][:5]
        gamesFromPredictions = [gameStore.gameById(gid) for gid in gids]
        gamesFromPredictions = [g for g in gamesFromPredictions if g is not None] # just in case
        gamesToAnalyse = gamesFromPredictions + gameStore.randomGamesWithoutAnalysis(10 - len(gids), excludeIds=gamesFromPredictions)
    else:
        gamesToAnalyse = gameStore.randomGamesWithoutAnalysis()

    if len(player.mustAnalyse) > 0:
        games = [gameStore.gameById(gid) for gid in player.mustAnalyse]
        mustAnalyseGames = [game for game in games if game is not None]
        gamesToAnalyse = gamesToAnalyse + mustAnalyseGames

    # analyse games with SF
    sumGamestoAnalyse = len(gamesToAnalyse)
    for i, game in enumerate(gamesToAnalyse):
        gameStore.addAnalysedGame(
            AnalysedGame.fromGame(
                game=game,
                engine=env.engine,
                infoHandler=env.infoHandler,
                white=game.white == userId,
                nodes=env.settings['stockfish']['nodes'],
                analysedPositionDB=env.analysedPositionDB
            ))
        # update progress for logging
        env.deepPlayerQueueDB.updateProgress(deepPlayerQueue.id, int(100*i/sumGamestoAnalyse))

    env.analysedGameDB.lazyWriteAnalysedGames(gameStore.analysedGames)

    logging.info('Posting report for ' + userId)
    env.api.postReport(env.irwin.report(
        player=player,
        gameStore=gameStore,
        owner=str(settings.name)))
    env.deepPlayerQueueDB.complete(deepPlayerQueue)

    # do this last. Reset games that must be analysed
    env.playerDB.write(Player.fromPlayerData(playerData))

    # engine likes to die abruptly after a while. Kill it before it gets the chance
    env.restartEngine()
