from modules.db.DBManager import DBManager
from modules.irwin.training.Training import Training
from conf.ConfigWrapper import ConfigWrapper
from modules.irwin.training.Env import Env

config = ConfigWrapper.new('conf/server_config.json')
dbManager = DBManager(config)
env = Env(config, dbManager.db())
training = Training(env)

training.analysedModelTraining.train(epochs = 2, filtered = False)