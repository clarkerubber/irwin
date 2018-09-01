from default_imports import *

import sys
import time

from conf.ConfigWrapper import ConfigWrapper

from modules.game.Game import Game, GameDB
from modules.game.AnalysedPosition import AnalysedPositionDB
from modules.game.AnalysedGame import AnalysedGameBSONHandler
from modules.game.EngineTools import EngineTools

from modules.db.DBManager import DBManager

from modules.client.Env import Env
from modules.client.Api import Api


conf = ConfigWrapper.new('conf/client_config.json')

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
logging.getLogger("modules.fishnet.fishnet").setLevel(logging.INFO)

env = Env(conf)
api = Api(env)

while True:
    logging.info('getting new job')
    job = api.requestJob()

    if job is not None:
        logging.warning(f'Analysing Player: {job.playerId}')

        analysedGames = []
        for game in job.games:
            logging.warning(f'Analysing Game: {game.id}')
            analysedGame = env.engineTools.analyseGame(game, game.white == job.playerId, conf['stockfish nodes'])
            if analysedGame is not None:
                analysedGames.append(analysedGame)

        response = api.completeJob(job, analysedGames)

        if response is not None:
            resJson = response.json()
            if response.status_code == 200:
                logging.info('SUCCESS. Posted completed job. Message: {}'.format(resJson.get('message')))
            else:
                logging.warning('SOFT FAILURE. Failed to post completed job. Message: {}'.format(resJson.get('message')))
        else:
            logging.warning(f'HARD FAILURE. Failed to post job. No response from server.')
    else:
        logging.info('Job is None. Pausing')
        time.sleep(10)