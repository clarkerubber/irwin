import argparse
import sys
import logging
import json

from pprint import pprint

from modules.core.Game import Game
from modules.core.GameAnalysis import GameAnalysis
from modules.core.GameAnalysisStore import GameAnalysisStore
from modules.core.PlayerEngineStatusBus import PlayerEngineStatusBus

from Env import Env

config = {}
with open('conf/config.json') as confFile:
  config = json.load(confFile)
if config == {}:
  raise Exception('Config file empty or does not exist!')

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--learner", dest="learn", nargs="?",
                    default=False, const=True, help="does this bot learn")
parser.add_argument("--train", dest="train", nargs="?",
                    default=False, const=True, help="force training to start")
parser.add_argument("--no-report", dest="noreport", nargs="?",
                    default=False, const=True, help="disable posting of player reports")
parser.add_argument("--test", dest="test", nargs="?",
                    default=False, const=True, help="only test the neural networks performance")
parser.add_argument("--quiet", dest="loglevel",
                    default=logging.DEBUG, action="store_const", const=logging.INFO,
                    help="reduce the number of logged messages")
settings = parser.parse_args()

config['irwin']['learn'] = settings.learn

logging.basicConfig(format="%(message)s", level=settings.loglevel, stream=sys.stdout)
logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)
logging.getLogger("chess.uci").setLevel(logging.WARNING)

env = Env(config)
while True:
  env.irwin.train()

PlayerEngineStatusBus(env.playerDB, config, settings.learn).start()

while True and not settings.test:
  # Get player data
  #userId = env.api.getNextPlayerId()
  userId = 'clarkey'
  playerData = env.api.getPlayerData(userId)

  # pull what we already have on the player
  gameAnalysisStore = GameAnalysisStore([], [])
  gameAnalysisStore.addGames(env.gameDB.byUserId(userId))
  gameAnalysisStore.addGameAnalyses(env.gameAnalysisDB.byUserId(userId))

  # Filter games and assessments for relevant info
  try:
    gameAnalysisStore.addGames([Game.fromDict(gid, userId, g) for gid, g in playerData['games'].items()])
  except KeyError:
    continue # if this doesn't gather any useful data, skip

  env.gameDB.lazyWriteGames(gameAnalysisStore.games)

  logging.debug("Already Analysed: " + str(len(gameAnalysisStore.gameAnalyses)))

  gameAnalysisStore.addGameAnalyses([GameAnalysis.fromGame(game, env.engine, env.infoHandler, game.white == userId, config['stockfish']['nodes']) for game in gameAnalysisStore.randomGamesWithoutAnalysis()])

  env.gameAnalysisDB.lazyWriteGameAnalyses(gameAnalysisStore.gameAnalyses)
"""
  if not settings.noassess:
    playerAnalysis = env.irwin.assessPlayer(PlayerAnalysis(
      id = userId,
      titled = 'title' in playerData['assessment']['user'].keys(),
      engine = None,
      gamesPlayed = playerData['assessment']['user']['games'],
      closedReports = sum(int(r.get('processedBy', None) is not None) for r in playerData['history'] if r['type'] == 'report' and r['data']['reason'] == 'cheat'),
      gameAnalyses = gameAnalyses,
      gamesActivation = None))

  env.playerAnalysisDB.write(playerAnalysis)
  if not settings.noreport:
    env.api.postReport(playerAnalysis.report(config['irwin']['thresholds']))
"""