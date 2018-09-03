from default_imports import *

from conf.ConfigWrapper import ConfigWrapper

from modules.irwin.Env import Env

from modules.irwin.training.AnalysedModelTraining import AnalysedModelTraining
from modules.irwin.training.BasicModelTraining import BasicModelTraining
from modules.irwin.training.Evaluation import Evaluation

from modules.irwin.AnalysedGameModel import AnalysedGameModel
from modules.irwin.BasicGameModel import BasicGameModel


class Training:
    def __init__(self, env: Env, newmodel: bool = False):
        self.analysedModelTraining = AnalysedModelTraining(
            env=env,
            analysedGameModel=AnalysedGameModel(env.config, newmodel))

        self.basicModelTraining = BasicModelTraining(
            env=env,
            basicGameModel=BasicGameModel(env.config, newmodel))

        self.evaluation = Evaluation(env, env.config)