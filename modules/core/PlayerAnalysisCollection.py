import requests
import threading
import json
import logging

from modules.core.Game import Game
from modules.core.GameAnalysisStore import GameAnalysisStore

class PlayerAnalysisCollection(threading.Thread):
  def __init__(self, env):
    threading.Thread.__init__(self)
    self.env = env

  def run(self):
    engines = self.env.playerDB.byEngine(True)
    legits = self.env.playerDB.byEngine(False)
    length = len(engines+legits)
    for i, p in enumerate(engines + legits):
      if i > 4763:
        logging.debug('Getting player data for '+p.id + '  -  '+str(i)+'/'+str(length))
        playerData = self.env.api.getPlayerData(p.id)

        # pull what we already have on the player
        gameAnalysisStore = GameAnalysisStore.new()

        # Filter games and assessments for relevant info
        try:
          gameAnalysisStore.addGames([Game.fromDict(gid, p.id, g) for gid, g in playerData['games'].items() if (g.get('initialFen') is None and g.get('variant') is None)])
        except KeyError:
          continue # if this doesn't gather any useful data, skip

        self.env.gameDB.lazyWriteGames(gameAnalysisStore.games)