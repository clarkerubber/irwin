from default_imports import *

from modules.queue.Origin import Origin
from modules.game.Player import Player
from modules.game.Game import Game

class Request(NamedTuple('Request', [
        ('origin', Origin),
        ('player', Player),
        ('games', List[Game])
    ])):
    @staticmethod
    def fromJson(json): # Opt[Request]
        try:
            return Request(
                origin = json['origin'],
                player = Player.fromJson(json['user']),
                games = [Game.fromJson(game) for game in json['games']]
                )
        except KeyError:
            logging.debug('key error mofo')
            return None