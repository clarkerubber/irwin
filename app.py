from conf.ConfigWrapper import ConfigWrapper

from webapp.Env import Env

from modules.db.DBManager import DBManager

from flask import Flask

from webapp.controllers.api.blueprint import buildApiBlueprint


config = ConfigWrapper.new('conf/server_config.json')

## Database
dbManager = DBManager(config)

## Modules
#auth = Auth(AuthEnv(config, dbManager.db()))

env = Env(config)

app = Flask(__name__)

apiBlueprint = buildApiBlueprint(env)

app.register_blueprint(apiBlueprint)

if __name__ == "__main__":
	app.run(host="0.0.0.0", debug=True)