from default_imports import *

from conf.ConfigWrapper import ConfigWrapper

from modules.irwin.Env import Env

from modules.irwin.training.AnalysedModelTraining import AnalysedModelTraining
from modules.irwin.training.BasicModelTraining import BasicModelTraining

from modules.irwin.AnalysedGameModel import AnalysedGameModel
from modules.irwin.BasicGameModel import BasicGameModel

class Training:
    def __init__(self, env: Env):
        self.analysedModelTraining = AnalysedModelTraining(env = env, analysedGameModel = AnalysedGameModel(env.config))
        self.basicModelTraining = BasicModelTraining(env = env, basicGameModel = BasicGameModel(env.config))