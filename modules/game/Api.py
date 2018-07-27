from default_imports import *

from modules.game.AnalysedGame import AnalysedGameBSONHandler

from modules.game.Env import Env

class Api(NamedTuple('Api', [
        ('env', Env)
    ])):
    def insertAnalysedGames(self, analysedGamesBSON: List[Dict]) -> bool:
        try:
            analysedGames = [AnalysedGameBSONHandler.reads(g) for g in analysedGamesBSON]
            self.env.analysedGameDB.lazyWriteMany(analysedGames)
            return True
        except (KeyError, ValueError):
            logging.warning('Malformed analysedGamesBSON: ' + str(analysedGamesBSON))
        return False