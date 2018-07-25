from default_imports import *

from conf.ConfigWrapper import ConfigWrapper

from modules.game.Game import Game, GameDB
from modules.game.AnalysedPosition import AnalysedPositionDB
from modules.game.AnalysedGame import AnalysedGameBSONHandler
from modules.game.EngineTools import EngineTools
from modules.db.DBManager import DBManager

from modules.client.Env import Env
from modules.client.Api import Api

import sys

from pprint import pprint

conf = ConfigWrapper.new('conf/client_config.json')

loglevels = {
    'WARNING': logging.WARNING,
    'INFO': logging.INFO
}

logging.basicConfig(format="%(message)s", level=loglevels[conf.loglevel], stream=sys.stdout)
logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)
logging.getLogger("chess.uci").setLevel(logging.WARNING)
logging.getLogger("modules.fishnet.fishnet").setLevel(logging.INFO)

env = Env(conf)
api = Api(env)

logging.info('getting new job to analyse')
job = api.requestJob()

if job is not None:
    logging.warning(f'Analysing player: {job.playerId}')
    analysedGames = {}
    for game in job.games[:10]:
        logging.warning(f'Analysing: {game.id}')
        analysedGame = env.engineTools.analyseGame(game, game.white == job.playerId, conf['stockfish nodes'])
        if analysedGame is not None:
            analysedGames[analysedGame.id] = AnalysedGameBSONHandler.writes(analysedGame)