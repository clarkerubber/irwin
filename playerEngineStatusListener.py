import json

from Env import Env
from modules.core.PlayerEngineStatusBus import PlayerEngineStatusBus

config = {}
with open('conf/config.json') as confFile:
    config = json.load(confFile)
if config == {}:
    raise Exception('Config file empty or does not exist!')

env = Env(config)

playerEngineStatusBus = PlayerEngineStatusBus(env.playerDB, env.settings)
playerEngineStatusBus.start()