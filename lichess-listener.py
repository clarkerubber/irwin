"""Stream listener for Irwin. Acts on player status updates, and analysis requests"""
from default_imports import *

from conf.ConfigWrapper import ConfigWrapper

import requests
from requests.exceptions import ChunkedEncodingError, ConnectionError
from requests.packages.urllib3.exceptions import NewConnectionError, ProtocolError, MaxRetryError
from http.client import IncompleteRead
from socket import gaierror 

from webapp.Env import Env

from modules.lichess.Request import Request

from modules.queue.EngineQueue import EngineQueue

import json
import argparse
import logging
import sys
from datetime import datetime, timedelta
from time import sleep

parser = argparse.ArgumentParser(description=__doc__)

parser.add_argument("--quiet", dest="loglevel",
                    default=logging.DEBUG, action="store_const", const=logging.INFO,
                    help="reduce the number of logged messages")
settings = parser.parse_args()

logging.basicConfig(format="%(message)s", level=settings.loglevel, stream=sys.stdout)
logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)
logging.getLogger("chess.uci").setLevel(logging.WARNING)
logging.getLogger("modules.fishnet.fishnet").setLevel(logging.WARNING)


config = ConfigWrapper.new('conf/server_config.json')

env = Env(config)

"""
Possible messages that lichess will emit

{'t':'request', 'origin': 'moderator', 'user': {'id': 'userId', 'titled': bool, 'engine': bool, 'games': int}, 'games': [<game>]}
"""

def handleLine(payload: Dict):
    request = Request.fromJson(payload)
    playerId = request.player.id
    if request is not None:
        logging.info(f'Processing request for {request.player}')
        # store upser
        env.gameApi.writePlayer(request.player)
        # store games
        env.gameApi.writeGames(request.games)

        existingEngineQueue = env.queue.engineQueueById(playerId)

        newEngineQueue = EngineQueue.new(
            playerId=playerId,
            origin=request.origin,
            gamesAndPredictions=list(zip(request.games, env.irwin.basicGameModel.predict(playerId, request.games))))

        if existingEngineQueue is not None and not existingEngineQueue.completed:
            newEngineQueue = EngineQueue.merge(existingEngineQueue, newEngineQueue)

        env.queue.queueEngineAnalysis(newEngineQueue)

while True:
    try:
        r = requests.get(
            config.api.url + 'api/stream/irwin',
            headers = {
                'User-Agent': 'Irwin',
                'Authorization': f'Bearer {config.api.token}'
            },
            stream = True
        )
        for line in r.iter_lines():
            try:
                payload = json.loads(line.decode("utf-8"))
                handleLine(payload)
            except json.decoder.JSONDecodeError:
                logging.warning(f"Failed to decode: {line.text}")
    except (ChunkedEncodingError, ConnectionError, NewConnectionError, ProtocolError, MaxRetryError, IncompleteRead, gaierror):
        sleep(5)
        continue
