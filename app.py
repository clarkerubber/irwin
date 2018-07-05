from webapp.Env import Env as WebEnv

from modules.auth.Auth import Auth
from modules.auth.Env import Env as AuthEnv

from modules.db.DBManager import DBManager

from flask import Flask

from webapp.controllers.api.blueprint import buildApiBlueprint

import json

config = {}
with open('conf/server_config.json') as confFile:
    config = json.load(confFile)
if config == {}:
    raise Exception('Config file empty or does not exist!')

## Database
dbManager = DBManager(config)

## Modules
auth = Auth(AuthEnv(config, dbManager.db()))

webEnv = WebEnv(config)

app = Flask(__name__)

app.register_blueprint(buildApiBlueprint(webEnv, auth))

if __name__ == "__main__":
	app.run(host="0.0.0.0", debug=True)