from default_imports import *

from modules.game.AnalysedGame import AnalysedGameBSONHandler

from modules.game.Env import Env

from modules.game.Player import Player
from modules.game.Player import PlayerID
from modules.game.Game import Game

class Api(NamedTuple('Api', [
        ('env', Env)
    ])):
    def writeAnalysedGames(self, analysedGamesBSON: List[Dict]) -> bool:
        try:
            analysedGames = [AnalysedGameBSONHandler.reads(g) for g in analysedGamesBSON]
            self.env.analysedGameDB.writeMany(analysedGames)
            return True
        except (KeyError, ValueError):
            logging.warning('Malformed analysedGamesBSON: ' + str(analysedGamesBSON))
        return False

    def gamesForAnalysis(self, playerId: PlayerID, required: List[str] = []) -> List[Game]:
        """
        Given a playerId and an amount of games. This function will return the games within `limit`
        that should be analysed
        """
        games = self.env.gameDB.byPlayerId(playerId)
        analysedGames = self.env.analysedGameDB.byPlayerId(playerId)

        gameIds = {g.id for g in games}
        analysedGameIds = {g.gameId for g in analysedGames}

        notAnalysedIds = gameIds - analysedGameIds

        games = [g for g in games if g.id in (notAnalysedIds | set(required))]

        return games

    def writeGames(self, games: List[Game]):
        """
        Store games from lichess
        """
        self.env.gameDB.writeMany(games)

    def writePlayer(self, player: Player):
        """
        Upsert a new player to the db
        """
        self.env.playerDB.write(player)