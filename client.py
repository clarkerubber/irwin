from default_imports import *

import argparse
import sys
import time
import json

from conf.ConfigWrapper import ConfigWrapper

from modules.game.Game import Game, GameDB
from modules.game.AnalysedPosition import AnalysedPositionDB
from modules.game.AnalysedGame import AnalysedGame
from modules.game.EngineTools import EngineTools

from modules.db.DBManager import DBManager

from modules.client.Env import Env
from modules.client.Api import Api


conf = ConfigWrapper.new('conf/client_config.json')

parser = argparse.ArgumentParser(description=__doc__)
## Training
parser.add_argument("--token", dest="token", nargs="?",
                default=None, help="token to use with webserver")

loglevels = {
    'CRITICAL': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
    'NOTSET': logging.NOTSET
}

logging.basicConfig(format="%(message)s", level=loglevels[conf.loglevel], stream=sys.stdout)
logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)
logging.getLogger("chess.uci").setLevel(logging.WARNING)
logging.getLogger("modules.fishnet.fishnet").setLevel(logging.WARNING)

args = parser.parse_args()

env = Env(conf, token = args.token)
api = Api(env)

def analyseGames(games: List[Game], playerId: str) -> Iterable[AnalysedGame]:
    """
    Iterate through list of games and return analysed games
    """

    count = len(games)
    for i, game in enumerate(games):
        logging.warning(f'{playerId}: Analysing Game #{i} / {count}: {game.id}')
        analysedGame = env.engineTools.analyseGame(game, game.white == playerId, conf['stockfish nodes'])
        if analysedGame is not None:
            yield analysedGame

while True:
    logging.info('getting new job')
    job = api.requestJob()

    if job is not None:
        logging.warning(f'Analysing Player: {job.playerId}')
        gameIds = [g.id for g in job.games]
        logging.warning(f'Analysing Games: {gameIds}')

        analysedGames = list(analyseGames(job.games, job.playerId))

        response = api.completeJob(job, analysedGames)

        if response is not None:
            try:
                resJson = response.json()
                if response.status_code == 200:
                    logging.info('SUCCESS. Posted completed job. Message: {}'.format(resJson.get('message')))
                else:
                    logging.warning('SOFT FAILURE. Failed to post completed job. Message: {}'.format(resJson.get('message')))
            except json.decoder.JSONDecodeError:
                logging.warning(f'HARD FAILURE. Failed to post job. Bad response from server.')
    else:
        logging.warning('Job is None. Pausing')
        time.sleep(10)
