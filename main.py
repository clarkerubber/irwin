import argparse
import chess
import chess.uci
import chess.pgn
import os
import sys
import logging
from pprint import pprint

import pymongo
from pymongo import MongoClient

from modules.api.api import getPlayerData, getPlayerId, postReport
from modules.Game import Game, recentGames, GameDB
from modules.PlayerAssessment import PlayerAssessment, PlayerAssessments, PlayerAssessmentDB

from modules.fishnet.fishnet import stockfish_command

sys.setrecursionlimit(2000)

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

engine = chess.uci.popen_engine(stockfish_command())
engine.setoption({'Threads': settings.threads, 'Hash': settings.memory})
engine.uci()
info_handler = chess.uci.InfoHandler()
engine.info_handlers.append(info_handler)

# Set up mongodb
client = MongoClient()
db = client.irwin
playerColl = db.player
gameColl = db.game
assessColl = db.assessments

gameDB = GameDB(gameColl)
playerAssessmentDB = PlayerAssessmentDB(assessColl)


# Get player data
userId = getPlayerId(settings.token)
userData = getPlayerData(userId, settings.token)

# Filter games and assessments for relevant info
try:
  playerAssessments = PlayerAssessments(userData['assessment']['playerAssessments'])
except KeyError:
  playerAssessments = PlayerAssessments([])

games = recentGames(playerAssessments.list, userData['games'])

# Write stuff to mongo
playerAssessmentDB.lazyWriteMany(playerAssessments)
gameDB.lazyWriteGames(games)

games = gameDB.byUserId(userId)
playerAssessments = playerAssessmentDB.byUserId(userId)

print(games)
print(playerAssessments)