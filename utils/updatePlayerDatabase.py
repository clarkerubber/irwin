"""Update data on players in the database"""
import logging

from modules.game.Player import Player
from modules.game.Game import Game
from modules.game.GameStore import GameStore

def updatePlayerDatabase(env):
    players= env.playerDB.all()
    length = len(players)
    for i, p in enumerate(players):
        logging.info('Getting player data for '+p.id + '  -  '+str(i)+'/'+str(length))
        playerData = env.api.getPlayerData(p.id)
        if playerData is not None:
            env.playerDB.write(Player.fromPlayerData(playerData))
            env.gameDB.writeMany(Game.fromPlayerData(playerData))