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

from modules.api.api import get_player_data, get_player_id, post_report
from modules.Game import Game, recent_games
from modules.PlayerAssessment import PlayerAssessment, PlayerAssessments

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

# Set up mongodb
client = MongoClient()
db = client.irwin
playerColl = db.player
gameColl = db.game
assessColl = db.assessments


# Get player data
user_id = get_player_id(settings.token)
user_data = get_player_data(user_id, settings.token)

# Filter games and assessments for relevant info
player_assessments = PlayerAssessments(user_data['assessment']['playerAssessments'])
recents = recent_games(player_assessments.list, user_data['games'])

# Write stuff to mongo
player_assessments.write(assessColl, player_assessments.byGameIds([p.id for p in recents]))
[g.write(gameColl) for g in recents]