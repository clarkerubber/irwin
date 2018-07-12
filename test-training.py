from default_imports import *

import sys

from pprint import pprint

from modules.db.DBManager import DBManager
from conf.ConfigWrapper import ConfigWrapper

from modules.irwin.Env import Env
from modules.irwin.Irwin import Irwin


logging.basicConfig(format="%(message)s", level=logging.INFO, stream=sys.stdout)
logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)
logging.getLogger("chess.uci").setLevel(logging.WARNING)
logging.getLogger("modules.fishnet.fishnet").setLevel(logging.INFO)


config = ConfigWrapper.new('conf/server_config.json')
dbManager = DBManager(config)
env = Env(config, dbManager.db())
irwin = Irwin(env)

playerId = 'clarkey'

player = env.playerDB.byId(playerId)
analysedGames = env.analysedGameDB.byPlayerId(playerId)

playerReport = irwin.createReport(player, analysedGames)

pprint(playerReport)
pprint(playerReport.reportDict())