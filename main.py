"""Main interface for Irwin"""

import argparse
import sys
import logging
import json

from modules.core.Game import Game
from modules.core.GameAnalysis import GameAnalysis
from modules.core.GameAnalysisStore import GameAnalysisStore
from modules.core.PlayerAnalysisCollection import PlayerAnalysisCollection


from Env import Env

config = {}
with open('conf/config.json') as confFile:
    config = json.load(confFile)
if config == {}:
    raise Exception('Config file empty or does not exist!')

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--trainbasic", dest="trainbasic", nargs="?",
                    default=False, const=True, help="train basic game model")
parser.add_argument("--trainanalysed", dest="trainanalysed", nargs="?",
                    default=False, const=True, help="train analysed game model")
parser.add_argument("--filtered", dest="filtered", nargs="?",
                    default=False, const=True, help="use filtered dataset for training")
parser.add_argument("--newmodel", dest="newmodel", nargs="?",
                    default=False, const=True, help="throw out current model. build new")

parser.add_argument("--buildactivationtable", dest="buildactivationtable", nargs="?",
                    default=False, const=True,
                    help="build table of game analysis that the network is confident in predicting")
parser.add_argument("--collectanalyses", dest="collectanalyses", nargs="?",
                    default=False, const=True,
                    help="collect game analyses for players. Build database collection")

parser.add_argument("--eval", dest="eval", nargs="?",
                    default=False, const=True,
                    help="evaluate the performance of neural networks")
parser.add_argument("--test", dest="test", nargs="?",
                    default=False, const=True, help="test on a single player")
parser.add_argument("--discover", dest="discover", nargs="?",
                    default=False, const=True,
                    help="search for cheaters in the database that haven't been marked")
parser.add_argument("--queuebuilder", dest="queuebuilder", nargs="?",
                    default=False, const=True,
                    help="pull player data from lichess and build a ranked queue")

parser.add_argument("--quiet", dest="loglevel",
                    default=logging.DEBUG, action="store_const", const=logging.INFO,
                    help="reduce the number of logged messages")
settings = parser.parse_args()

logging.basicConfig(format="%(message)s", level=settings.loglevel, stream=sys.stdout)
logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)
logging.getLogger("chess.uci").setLevel(logging.WARNING)
logging.getLogger("modules.fishnet.fishnet").setLevel(logging.INFO)

env = Env(config)

if settings.collectanalyses:
    playerAnalysisCollectionThread = PlayerAnalysisCollection(env)
    playerAnalysisCollectionThread.start()

# train on a single batch
if settings.trainbasic:
    env.irwin.basicGameModel.train(config['irwin']['train']['epochs'], settings.newmodel)

if settings.buildactivationtable:
    env.irwin.buildActivationTable()

if settings.trainanalysed:
    env.irwin.analysedGameModel.train(
        config['irwin']['train']['epochs'],
        settings.filtered, settings.newmodel)

# test on a single user in the DB
if settings.test:
    for userId in ['chess-network', 'clarkey', 'thibault', 'uyfadcrack']:
        gameAnalysisStore = GameAnalysisStore.new()
        gameAnalysisStore.addGames(env.gameDB.byUserId(userId))
        gameAnalysisStore.addGameAnalyses(env.gameAnalysisDB.byUserId(userId))
        env.api.postReport(env.irwin.report(userId, gameAnalysisStore))
        logging.debug("posted")

# how good is the network?
if settings.eval:
    env.irwin.evaluate()

if settings.discover:
    env.irwin.discover()

if settings.queuebuilder:
    pass # we'll get to this later

if not (settings.trainbasic
        or settings.trainanalysed
        or settings.eval
        or settings.test
        or settings.buildactivationtable
        or settings.collectanalyses
        or settings.queuebuilder):
    while True:
        logging.debug('Getting new player ID')
        userId = env.api.getNextPlayerId()
        logging.warning('Getting player data for '+userId)
        playerData = env.api.getPlayerData(userId)

        if playerData is None:
            logging.warning("getPlayerData returned None in main.py")
            continue

        # pull what we already have on the player
        gameAnalysisStore = GameAnalysisStore.new()
        gameAnalysisStore.addGames(env.gameDB.byUserId(userId))
        gameAnalysisStore.addGameAnalyses(env.gameAnalysisDB.byUserId(userId))

        # Filter games and assessments for relevant info
        try:
            gameAnalysisStore.addGames(
                [Game.fromDict(gid, userId, g) for gid, g in playerData['games'].items() \
                 if g.get('initialFen') is None and g.get('variant') is None])
        except KeyError:
            logging.warning("KeyError warning when adding games to analysisStore in main.py")
            continue # if this doesn't gather any useful data, skip

        env.gameDB.lazyWriteGames(gameAnalysisStore.games)

        logging.debug("Already Analysed: " + str(len(gameAnalysisStore.gameAnalyses)))

        # decide which games should be analysed
        gameTensors = gameAnalysisStore.gameTensorsWithoutAnalysis(userId)

        if gameTensors is not None:
            gamePredictions = env.irwin.predictBasicGames(gameTensors) # [(gameIds, predictions)]
            if gamePredictions is None:
                logging.warning("gamePredictions is None in main.py")
                continue
            gamePredictions.sort(key=lambda tup: -tup[1])
            gids = [gid for gid, _ in gamePredictions][:5]
            gamesFromPredictions = [gameAnalysisStore.gameById(gid) for gid in gids]
            gamesFromPredictions = [g for g in gamesFromPredictions if g is not None] # just in case
            gamesToAnalyse = gamesFromPredictions + gameAnalysisStore.randomGamesWithoutAnalysis(10 - len(gids), excludeIds=gamesFromPredictions)
        else:
            gamesToAnalyse = gameAnalysisStore.randomGamesWithoutAnalysis()

        # analyse games with SF
        gameAnalysisStore.addGameAnalyses([
            GameAnalysis.fromGame(
                game,
                env.engine,
                env.infoHandler,
                game.white == userId,
                env.settings['stockfish']['nodes']) for game in gamesToAnalyse])

        env.gameAnalysisDB.lazyWriteGameAnalyses(gameAnalysisStore.gameAnalyses)

        logging.warning('Posting report for ' + userId)
        env.api.postReport(env.irwin.report(userId, gameAnalysisStore))
        env.restartEngine()
