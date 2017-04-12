import argparse
#import chess
#import chess.uci
#import chess.pgn
#import os
import sys
import logging
from pprint import pprint
from modules.bcolors.bcolors import bcolors

from modules.api import getPlayerData, getPlayerId, postReport

from modules.Game import Game, recentGames
from modules.PlayerAssessment import PlayerAssessmentBSONHandler, PlayerAssessment, PlayerAssessments
from modules.GameAnalysis import GameAnalysis, GameAnalyses, analyse

from env import IrwinEnv

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("token", metavar="TOKEN",
                    help="secret token for the lichess api")
parser.add_argument("train", metavar="TRAIN",
                    help="does this bot learn", nargs="?", type=int, default=1)
parser.add_argument("threads", metavar="THREADS", nargs="?", type=int, default=4,
                    help="number of engine threads")
parser.add_argument("memory", metavar="MEMORY", nargs="?", type=int, default=2048,
                    help="memory in MB to use for engine hashtables")
parser.add_argument("--quiet", dest="loglevel",
                    default=logging.DEBUG, action="store_const", const=logging.INFO,
                    help="substantially reduce the number of logged messages")
settings = parser.parse_args()

try:
  # Optionally fix colors on Windows and in journals if the colorama module
  # is available.
  import colorama
  wrapper = colorama.AnsiToWin32(sys.stdout)
  if wrapper.should_wrap():
    sys.stdout = wrapper.stream
except ImportError:
  pass

logging.basicConfig(format="%(message)s", level=settings.loglevel, stream=sys.stdout)
logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)
logging.getLogger("chess.uci").setLevel(logging.WARNING)

env = IrwinEnv(settings)

while True:
  # Get player data
  userId = getPlayerId(settings.token)
  userData = getPlayerData(userId, settings.token)

  # Filter games and assessments for relevant info
  try:
    pas = list([PlayerAssessmentBSONHandler.reads(pa) for pa in userData['assessment']['playerAssessments']])
    playerAssessments = PlayerAssessments(pas)
    games = recentGames(playerAssessments, userData['games'])
  except KeyError:
    continue # if either of these don't gather any useful data, skip them

  # Write stuff to mongo
  env.playerAssessmentDB.lazyWriteMany(playerAssessments)
  env.gameDB.lazyWriteGames(games)

  # Pull everything from mongo that we have on the player
  playerAssessments = env.playerAssessmentDB.byUserId(userId)
  games = env.gameDB.byIds(playerAssessments.gameIds())
  gameAnalyses = env.gameAnalysisDB.byUserId(userId)

  logging.debug(bcolors.WARNING + "Already Analysed: " + str(len(gameAnalyses.gameAnalyses)) + bcolors.ENDC)

  for g in games.games:
    if playerAssessments.hasGameId(g.id):
      gameAnalyses.append(GameAnalysis(g, playerAssessments.byGameId(g.id), []))

  gameAnalyses.analyse(env.engine, env.infoHandler)

  env.gameAnalysisDB.lazyWriteGames(gameAnalyses)