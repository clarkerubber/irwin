"""Update data on players in the database"""
import threading
import logging

from modules.core.Game import Game
from modules.core.GameAnalysisStore import GameAnalysisStore

class UpdatePlayerDatabase(threading.Thread):
    def __init__(self, env):
        threading.Thread.__init__(self)
        self.env = env

    def run(self):
        players= self.env.playerDB.all()
        length = len(players)
        for i, p in enumerate(players):
            logging.info('Getting player data for '+p.id + '  -  '+str(i)+'/'+str(length))
            playerData = self.env.api.getPlayerData(p.id)
            self.env.playerDB.write(Player.fromPlayerData(playerData))
            self.env.gameDB.lazyWriteGames([Game.fromPlayerData(playerData)])