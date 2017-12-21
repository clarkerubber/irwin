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

from Env import Env
from GatherDataThread import GatherDataThread

config = {}
with open('conf/config.json') as confFile:
  config = json.load(confFile)
if config == {}:
  raise Exception('Config file empty or does not exist!')

parser = argparse.ArgumentParser(description=__doc__)
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
parser.add_argument("--gather", dest="gather", nargs="?",
                    default=False, const=True, help="collect and analyse players forever to build dataset. Does not use models and does not post results")
parser.add_argument("--newmodel", dest="newmodel", nargs="?",
                    default=False, const=True, help="generate a new model for training")
parser.add_argument("--no-report", dest="noreport", nargs="?",
                    default=False, const=True, help="disable posting of player reports")
parser.add_argument("--eval", dest="eval", nargs="?",
                    default=False, const=True, help="evaluate the performance of neural networks")
parser.add_argument("--buildpivottable", dest="buildpivottable", nargs="?",
                    default=False, const=True, help="build table relating game analysis to players, game length and engine status")
parser.add_argument("--buildconfidencetable", dest="buildconfidencetable", nargs="?",
                    default=False, const=True, help="build table of game analysis that the network is confident in predicting")
parser.add_argument("--buildplayertable", dest="buildplayertable", nargs="?",
                    default=False, const=True, help="build table of game analyses against player names and engine status")
parser.add_argument("--test", dest="test", nargs="?",
                    default=False, const=True, help="test on a single player")
parser.add_argument("--quiet", dest="loglevel",
                    default=logging.DEBUG, action="store_const", const=logging.INFO,
                    help="reduce the number of logged messages")
settings = parser.parse_args()

logging.basicConfig(format="%(message)s", level=settings.loglevel, stream=sys.stdout)
logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)
logging.getLogger("chess.uci").setLevel(logging.WARNING)

env = Env(config)

# start the bus to update player engine status
playerEngineStatusBus = PlayerEngineStatusBus(env.playerDB, env.settings)
playerEngineStatusBus.start()

# test on a single user in the DB
if settings.test:
  gameModel = env.irwin.narrowGameModel.model()
  playerModel = env.irwin.playerModel.model()
  for userId in ['bizaro90','tonno3','tidper','papiiii988','remedy93','asachenkoksenia','chinesecheckersgm','captainsolo','zaher72k','armen2888','j152436','saidaluap','thesrinivaskumar','saulrosa','maximuss21','jsales','actualfish','chessszogun','fagundes','ule','lighthouseinacup','perdorio','trahtrah']:
    gameAnalysisStore = GameAnalysisStore.new()
    gameAnalysisStore.addGames(env.gameDB.byUserId(userId))
    gameAnalysisStore.addGameAnalyses(env.gameAnalysisDB.byUserId(userId))

    env.api.postReport(env.irwin.report(userId, gameAnalysisStore, gameModel, playerModel))
    print("posted")

if settings.epoch:
  env.irwin.buildPivotTable()
  env.irwin.generalGameModel.train(config['irwin']['train']['batchSize'], config['irwin']['train']['epochs'])
  env.irwin.buildConfidenceTable()
  env.irwin.narrowGameModel.train(config['irwin']['train']['batchSize'], config['irwin']['train']['epochs'])

while settings.epochforever:
  env.irwin.buildPivotTable()
  env.irwin.genearlGameModel.train(config['irwin']['train']['batchSize'], config['irwin']['train']['epochs'])
  env.irwin.buildConfidenceTable()
  env.irwin.narrowGameModel.train(config['irwin']['train']['batchSize'], config['irwin']['train']['epochs'])

if settings.buildpivottable:
  env.irwin.buildPivotTable()

if settings.buildconfidencetable:
  env.irwin.buildConfidenceTable()

if settings.buildplayertable:
  env.irwin.buildPlayerGameActivationsTable()

# train on a single batch
if settings.traingeneral:
  env.irwin.generalGameModel.train(config['irwin']['train']['batchSize'], config['irwin']['train']['epochs'], settings.newmodel)

if settings.trainnarrow:
  env.irwin.narrowGameModel.train(config['irwin']['train']['batchSize'], config['irwin']['train']['epochs'], settings.newmodel)

if settings.trainplayer:
  env.irwin.playerModel.train(config['irwin']['train']['batchSize'], config['irwin']['train']['epochs'], settings.newmodel)

# how good is the network?
if settings.eval:
  env.irwin.evaluate()

# train forever
while settings.traingeneralforever:
  env.irwin.generalGameModel.train(config['irwin']['train']['batchSize'], config['irwin']['train']['epochs'], settings.newmodel)
  settings.newmodel = False

# train forever
if settings.trainnarrowforever:
  #env.irwin.buildConfidenceTable()
  while True:
    env.irwin.narrowGameModel.train(config['irwin']['train']['batchSize'], config['irwin']['train']['epochs'], settings.newmodel)
    settings.newmodel = False

if settings.trainplayerforever:
  while True:
    env.irwin.playerModel.train(config['irwin']['train']['batchSize'], config['irwin']['train']['epochs'], settings.newmodel)
    settings.newmodel = False

if settings.gather:
  [GatherDataThread(x, Env(config)).start() for x in range(env.settings['core']['instances'])]

if not (settings.traingeneral or settings.trainnarrow or settings.eval or settings.noreport or settings.test or settings.gather):
  while True:
    try:
      logging.debug('Getting new player ID')
      userId = env.api.getNextPlayerId()
      logging.debug('Getting player data for '+userId)
      playerData = env.api.getPlayerData(userId)

      # pull what we already have on the player
      gameAnalysisStore = GameAnalysisStore.new()
      gameAnalysisStore.addGames(env.gameDB.byUserId(userId))
      gameAnalysisStore.addGameAnalyses(env.gameAnalysisDB.byUserId(userId))

      # Filter games and assessments for relevant info
      try:
        gameAnalysisStore.addGames([Game.fromDict(gid, userId, g) for gid, g in playerData['games'].items() if (g.get('initialFen') is None and g.get('variant') is None)])
      except KeyError:
        continue # if this doesn't gather any useful data, skip

      env.gameDB.lazyWriteGames(gameAnalysisStore.games)

      logging.debug("Already Analysed: " + str(len(gameAnalysisStore.gameAnalyses)))

      gameAnalysisStore.addGameAnalyses([GameAnalysis.fromGame(game, env.engine, env.infoHandler, game.white == userId, env.settings['stockfish']['nodes']) for game in gameAnalysisStore.randomGamesWithoutAnalysis()])

      env.gameAnalysisDB.lazyWriteGameAnalyses(gameAnalysisStore.gameAnalyses)

      logging.warning('Posting report for ' + userId)
      env.api.postReport(env.irwin.report(userId, gameAnalysisStore))
    except:
      print("something important broke")
      os._exit(1)
print("exitting")
os._exit(1)