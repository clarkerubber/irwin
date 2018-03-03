"""Stream listener for Irwin. Acts on player status updates, and analysis requests"""
import requests
from requests.exceptions import ChunkedEncodingError, ConnectionError
from requests.packages.urllib3.exceptions import NewConnectionError, ProtocolError, MaxRetryError
from http.client import IncompleteRead
from socket import gaierror

import json
import argparse
import logging
import sys
from datetime import datetime, timedelta
from time import sleep

from modules.queue.BasicPlayerQueue import BasicPlayerQueue
from modules.queue.DeepPlayerQueue import DeepPlayerQueue
from modules.queue.ModReport import ModReport

from modules.game.Player import Player
from modules.game.Game import Game

from Env import Env

parser = argparse.ArgumentParser(description=__doc__)

parser.add_argument("--quiet", dest="loglevel",
                    default=logging.DEBUG, action="store_const", const=logging.INFO,
                    help="reduce the number of logged messages")
settings = parser.parse_args()

logging.basicConfig(format="%(message)s", level=settings.loglevel, stream=sys.stdout)
logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)
logging.getLogger("chess.uci").setLevel(logging.WARNING)
logging.getLogger("modules.fishnet.fishnet").setLevel(logging.WARNING)

config = {}
with open('conf/config.json') as confFile:
    config = json.load(confFile)
if config == {}:
    raise Exception('Config file empty or does not exist!')

env = Env(config, engine=False)

"""
Possible messages that lichess will emit
{"t":"request","origin":"moderator","user":"decidement"}
{"t":"request","origin":"tournament","user":"decidement"}
{"t":"request","origin":"leaderboard","user":"decidement"}
{"t":"reportCreated","user":"decidement"}
{"t":"reportProcessed","user":"qxxxx","marked":false}
{"t":"reportProcessed","user":"aliali1975","marked":true}
{"t":"mark","user":"aliali1975","marked":true}
{"t":"mark","user":"aliali1975","marked":false}
"""

def handleLine(lineDict):
    messageType = lineDict['t']
    userId = lineDict['user']

    playerData = env.api.getPlayerData(userId)
    if playerData is None:
        logging.warning("PlayerData is None. Returning None")
        return None
    player = Player.fromPlayerData(playerData)

    if player is not None:
        env.playerDB.write(player) # this will cover updating the player status
        env.gameDB.lazyWriteGames(Game.fromPlayerData(playerData)) # get games because data is king

        # check if this player has been analysed recently
        tooSoon = False # assume its not to start with
        timeSinceUpdated = env.playerReportDB.timeSinceUpdated(userId)

        if timeSinceUpdated is not None:
            # automatically analysing a player more than once a week is too soon
            if timeSinceUpdated < timedelta(weeks=1):
                logging.info("Too Soon " + str(timeSinceUpdated))
                tooSoon = True

        # check if there is already a request open for this player
        inQueue = env.deepPlayerQueueDB.exists(userId)

        # mod requests skip all queues
        if messageType == 'request':
            if lineDict['origin'] == 'moderator':
                env.deepPlayerQueueDB.write(
                    DeepPlayerQueue(id=userId, origin='moderator', owner=None, precedence=100000))
        
        # all other types of request
        if not tooSoon and not inQueue:
            if messageType == 'request':
                env.basicPlayerQueueDB.write(BasicPlayerQueue(id=userId, origin=lineDict['origin']))

            elif messageType == 'reportCreated' and not env.modReportDB.isOpen(userId):
                # don't update these if a report is still open
                # these will get re-queued by scan-update.py
                env.basicPlayerQueueDB.write(BasicPlayerQueue(id=userId, origin='report'))
                env.modReportDB.write(ModReport.new(userId))

        # closures and marks
        if messageType == 'reportProcessed' or messageType == 'mark':
            logging.info("removing all queue items")
            env.basicPlayerQueueDB.removeUserId(userId)
            env.deepPlayerQueueDB.removeUserId(userId)
            env.modReportDB.close(userId)
    else:
        logging.warning("player is None. Not proceeding.")


while True:
    try:
        r = requests.get(config['api']['url'] + 'irwin/stream?api_key=' + config['api']['token'], stream=True)
        for line in r.iter_lines():
            lineDict = json.loads(line.decode("utf-8"))
            logging.info("Received: " + str(lineDict))
            handleLine(lineDict)
    except ChunkedEncodingError:
        sleep(5)
        continue
    except ConnectionError:
        logging.warning("WARNING: ConnectionError")
        sleep(5)
        continue
    except NewConnectionError:
        logging.warning("WARNING: NewConnectionError")
        sleep(5)
        continue
    except ProtocolError:
        logging.warning("WARNING: ProtocolError")
        sleep(5)
        continue
    except MaxRetryError:
        logging.warning("WARNING: MaxRetryError")
        sleep(5)
        continue
    except IncompleteRead:
        logging.warning("WARNING: IncompleteRead")
        sleep(5)
        continue
    except gaierror:
        logging.warning("WARNING: gaierror")
        sleep(5)
        continue