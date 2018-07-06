from collections import namedtuple
import json

config = {}
with open('conf/client_config.json') as confFile:
    config = json.load(confFile)
if config == {}:
    raise Exception('Config file empty or does not exist!')