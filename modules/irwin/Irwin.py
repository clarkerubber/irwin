from default_imports import *

from modules.auth.Auth import AuthID

from modules.game.Player import Player
from modules.game.AnalysedGame import AnalysedGame

from modules.irwin.PlayerReport import PlayerReport
from modules.irwin.AnalysedGameModel import AnalysedGameModel
from modules.irwin.BasicGameModel import BasicGameModel

from modules.irwin.Env import Env

from modules.irwin.training.Training import Training

class Irwin:
    """
    Irwin(env: Env)

    The main thinking and evalutaion engine of the application.
    """
    def __init__(self, env: Env):
        self.env = env
        self.basicGameModel = BasicGameModel(env.config)
        self.analysedGameModel = AnalysedGameModel(env.config)
        self.training = Training(env)

    def createReport(self, player: Player, analysedGames: List[AnalysedGame], owner: AuthID = 'test'):
        playerPredictions = self.analysedGameModel.predict(analysedGames)
        playerReport = PlayerReport.new(player, zip(analysedGames, playerPredictions), owner)

        return playerReport