import argparse
import sys
import logging
import json
import threading
import copy
import time
import os

from pprint import pprint

from modules.core.Game import Game
from modules.core.GameAnalysis import GameAnalysis
from modules.core.GameAnalysisStore import GameAnalysisStore
from modules.core.PlayerEngineStatusBus import PlayerEngineStatusBus
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
parser.add_argument("--traingeneral", dest="traingeneral", nargs="?",
                    default=False, const=True, help="train general game model")
parser.add_argument("--traingeneralforever", dest="traingeneralforever", nargs="?",
                    default=False, const=True, help="train genearl model forever")
parser.add_argument("--trainnarrow", dest="trainnarrow", nargs="?",
                    default=False, const=True, help="train narrow game model")
parser.add_argument("--trainnarrowforever", dest="trainnarrowforever", nargs="?",
                    default=False, const=True, help="train narrow model forever")
parser.add_argument("--trainplayer", dest="trainplayer", nargs="?",
                    default=False, const=True, help="train player game model")
parser.add_argument("--trainplayerforever", dest="trainplayerforever", nargs="?",
                    default=False, const=True, help="train player game model forever")

parser.add_argument("--epoch", dest="epoch", nargs="?",
                    default=False, const=True, help="train from start to finish")
parser.add_argument("--epochforever", dest="epochforever", nargs="?",
                    default=False, const=True, help="train from start to finish forever")

parser.add_argument("--newmodel", dest="newmodel", nargs="?",
                    default=False, const=True, help="generate a new model for training")

parser.add_argument("--no-report", dest="noreport", nargs="?",
                    default=False, const=True, help="disable posting of player reports")

parser.add_argument("--buildpivottable", dest="buildpivottable", nargs="?",
                    default=False, const=True, help="build table relating game analysis to players, game length and engine status")
parser.add_argument("--buildconfidencetable", dest="buildconfidencetable", nargs="?",
                    default=False, const=True, help="build table of game analysis that the network is confident in predicting")
parser.add_argument("--buildplayertable", dest="buildplayertable", nargs="?",
                    default=False, const=True, help="build table of game analyses against player names and engine status")
parser.add_argument("--buildvocab", dest="buildvocab", nargs="?",
                    default=False, const=True, help="build table of words used to describe positions and games")
parser.add_argument("--collectanalyses", dest="collectanalyses", nargs="?",
                    default=False, const=True, help="collect game analyses for players. Build database collection")

parser.add_argument("--eval", dest="eval", nargs="?",
                    default=False, const=True, help="evaluate the performance of neural networks")
parser.add_argument("--test", dest="test", nargs="?",
                    default=False, const=True, help="test on a single player")
parser.add_argument("--discover", dest="discover", nargs="?",
                    default=False, const=True, help="search for cheaters in the database that haven't been marked")
parser.add_argument("--queuebuilder", dest="queuebuilder", nargs="?",
                    default=False, const=True, help="pull player data from lichess and build a ranked queue for irwin to analyse")
parser.add_argument("--quiet", dest="loglevel",
                    default=logging.DEBUG, action="store_const", const=logging.INFO,
                    help="reduce the number of logged messages")
settings = parser.parse_args()

env = Env(config)

logging.basicConfig(format="%(message)s", level=settings.loglevel, stream=sys.stdout)
logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)
logging.getLogger("chess.uci").setLevel(logging.WARNING)
logging.getLogger("modules.fishnet.fishnet").setLevel(logging.INFO)

if settings.collectanalyses:
  playerAnalysisCollectionThread = PlayerAnalysisCollection(env)
  playerAnalysisCollectionThread.start()

# test on a single user in the DB
if settings.test:
  for userId in ['chess-network']:
    gameAnalysisStore = GameAnalysisStore.new()
    gameAnalysisStore.addGames(env.gameDB.byUserId(userId))
    gameAnalysisStore.addGameAnalyses(env.gameAnalysisDB.byUserId(userId))
    env.api.postReport(env.irwin.report(userId, gameAnalysisStore))
    print("posted")

if settings.epoch:
  env.irwin.buildPivotTable()
  env.irwin.generalGameModel.train(config['irwin']['train']['batchSize'], config['irwin']['train']['epochs'], settings.newmodel)
  env.irwin.buildConfidenceTable()
  env.irwin.narrowGameModel.train(config['irwin']['train']['batchSize'], config['irwin']['train']['epochs'], settings.newmodel)
  env.irwin.buildPlayerGameActivationsTable()
  env.irwin.playerModel.train(config['irwin']['train']['batchSize'], config['irwin']['train']['epochs']*5, True)

if settings.epochforever:
  while True:
    env.irwin.generalGameModel.train(config['irwin']['train']['batchSize'], config['irwin']['train']['epochs'], settings.newmodel)
    env.irwin.buildConfidenceTable()
    env.irwin.narrowGameModel.train(config['irwin']['train']['batchSize'], config['irwin']['train']['epochs'], settings.newmodel)
    env.irwin.buildPlayerGameActivationsTable()
    env.irwin.playerModel.train(config['irwin']['train']['batchSize'], config['irwin']['train']['epochs']*5, True)
    settings.newmodel = False

if settings.buildpivottable:
  env.irwin.buildPivotTable()

if settings.buildconfidencetable:
  env.irwin.buildConfidenceTable()

if settings.buildvocab:
  env.irwin.buildVocabularly()

if settings.buildplayertable:
  env.irwin.buildPlayerGameActivationsTable()

# train on a single batch
if settings.trainbasic:
  env.irwin.gameModel.train(config['irwin']['train']['epochs'], settings.newmodel)

if settings.traingeneral:
  env.irwin.generalGameModel.train(config['irwin']['train']['epochs'], settings.newmodel)

if settings.trainnarrow:
  env.irwin.narrowGameModel.train(config['irwin']['train']['epochs'], settings.newmodel)

if settings.trainplayer:
  env.irwin.playerModel.train(config['irwin']['train']['epochs'], settings.newmodel)

# how good is the network?
if settings.eval:
  env.irwin.evaluate()

if settings.discover:
  env.irwin.discover()

# train forever
while settings.traingeneralforever:
  env.irwin.generalGameModel.train(config['irwin']['train']['epochs'], settings.newmodel)
  settings.newmodel = False

# train forever
if settings.trainnarrowforever:
  #env.irwin.buildConfidenceTable()
  while True:
    env.irwin.narrowGameModel.train(config['irwin']['train']['epochs'], settings.newmodel)
    settings.newmodel = False

if settings.trainplayerforever:
  while True:
    env.irwin.playerModel.train(config['irwin']['train']['epochs'], settings.newmodel)
    settings.newmodel = False

if settings.queuebuilder:
  while True:
    logging.debug('Getting new player ID')
    userId = env.api.getNextPlayerId()
    logging.debug('Getting player dara for '+userId)
    playerData = env.api.getPlayerData(userId)

    # pull what we already have on the player
    gameAnalysisStore = GameAnalysisStore.new()
    gameAnalysisStore.addGames(env.gameDB.byUserId(userId))
    gameAnalysisStore.addGameAnalyses(env.gameAnalysisDB.byUserId(userId))

    # Filter games and assessments for relevant info
    try:
      gameAnalysisStore.addGames([Game.fromDict(gid, userId, g) for gid, g in playerData['games'].items() if (g.get('initialFen') is None and g.get('variant') is None)])
    except KeyError:
      print("KeyError Warning")
      continue # if this doesn't gather any useful data, skip

    env.gameDB.lazyWriteGames(gameAnalysisStore.games)

    logging.debug("Already Analysed: " + str(len(gameAnalysisStore.gameAnalyses)))

    # decide which games should be analysed
    gameTensors = gameAnalysisStore.gameTensorsWithoutAnalysis(userId)

    if gameTensors is not None:
      gamePredictions = env.irwin.predictGames(gameTensors)
      gamePredictions.sort(key=lambda tup: -tup[1])
      gids = [gid for gid, p in gamePredictions][:5]
      gamesFromPredictions = [gameAnalysisStore.gameById(gid) for gid in gids]
      gamesFromPredictions = [g for g in gamesFromPredictions if g is not None] # just in case
      gamesToAnalyse = gamesFromPredictions + gameAnalysisStore.randomGamesWithoutAnalysis(10 - len(gids), excludeIds=gamesFromPredictions)
    else:
      gamesToAnalyse = gameAnalysisStore.randomGamesWithoutAnalysis()


if not (
  settings.traingeneral or
  settings.trainnarrow or
  settings.eval or
  settings.noreport or
  settings.test or
  settings.buildconfidencetable or
  settings.collectanalyses):
  while True:
    logging.debug('Getting new player ID')
    userId = env.api.getNextPlayerId()
    logging.debug('Getting player data for '+userId)
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
      gameAnalysisStore.addGames([Game.fromDict(gid, userId, g) for gid, g in playerData['games'].items() if (g.get('initialFen') is None and g.get('variant') is None)])
    except KeyError:
      logging.warning("KeyError warning when adding games to analysisStore in main.py")
      continue # if this doesn't gather any useful data, skip

    env.gameDB.lazyWriteGames(gameAnalysisStore.games)

    logging.debug("Already Analysed: " + str(len(gameAnalysisStore.gameAnalyses)))

    # decide which games should be analysed
    gameTensors = gameAnalysisStore.gameTensorsWithoutAnalysis(userId)

    if gameTensors is not None:
      gamePredictions = env.irwin.predictGames(gameTensors)
      if gamePredictions is None:
        logging.warning("gamePredictions is None in main.py")
        continue
      gamePredictions.sort(key=lambda tup: -tup[1])
      gids = [gid for gid, p in gamePredictions][:5]
      gamesFromPredictions = [gameAnalysisStore.gameById(gid) for gid in gids]
      gamesFromPredictions = [g for g in gamesFromPredictions if g is not None] # just in case
      gamesToAnalyse = gamesFromPredictions + gameAnalysisStore.randomGamesWithoutAnalysis(10 - len(gids), excludeIds=gamesFromPredictions)
    else:
      gamesToAnalyse = gameAnalysisStore.randomGamesWithoutAnalysis()

    # analyse games with SF
    gameAnalysisStore.addGameAnalyses([GameAnalysis.fromGame(game, env.engine, env.infoHandler, game.white == userId, env.settings['stockfish']['nodes']) for game in gameAnalysisStore.randomGamesWithoutAnalysis()])

    env.gameAnalysisDB.lazyWriteGameAnalyses(gameAnalysisStore.gameAnalyses)

    logging.warning('Posting report for ' + userId)
    env.api.postReport(env.irwin.report(userId, gameAnalysisStore))
    env.restartEngine()