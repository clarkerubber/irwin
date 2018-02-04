"""Update data on players in the database"""
import threading
import logging

from modules.core.Player import Player
from modules.core.Game import Game
from modules.core.GameAnalysisStore import GameAnalysisStore

def updatePlayerDatabase(env):
    players= env.playerDB.all()
    length = len(players)
    for i, p in enumerate(players):
        logging.info('Getting player data for '+p.id + '  -  '+str(i)+'/'+str(length))
        playerData = env.api.getPlayerData(p.id)
        if playerData is not None:
            env.playerDB.write(Player.fromPlayerData(playerData))
            env.gameDB.lazyWriteGames(Game.fromPlayerData(playerData))