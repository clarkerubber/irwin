from default_imports import *

from modules.auth.Auth import AuthID

from modules.game.Player import Player
from modules.game.AnalysedGame import GameAnalysedGame

from modules.irwin.PlayerReport import PlayerReport
from modules.irwin.AnalysedGameModel import AnalysedGameModel
from modules.irwin.BasicGameModel import BasicGameModel

from modules.irwin.Env import Env

from modules.irwin.training.Training import Training
from modules.irwin.training.Evaluation import Evaluation

class Irwin:
    """
    Irwin(env: Env)

    The main thinking and evalutaion engine of the application.
    """
    def __init__(self, env: Env, newmodel: bool = False):
        logging.debug('creating irwin instance')
        self.env = env
        self.basicGameModel = BasicGameModel(env.config)
        self.analysedGameModel = AnalysedGameModel(env.config)
        self.training = Training(env, newmodel)
        self.evaluation = Evaluation(self, self.env.config)

    def createReport(self, player: Player, gameAnalysedGames: List[GameAnalysedGame], owner: AuthID = 'test'):
        predictions = self.analysedGameModel.predict(gameAnalysedGames)
        playerReport = PlayerReport.new(player, [(ag, p) for ag, p in zip(gameAnalysedGames, predictions) if p is not None], owner)

        return playerReport