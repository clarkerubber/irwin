import threading
import logging

from modules.core.Game import Game
from modules.core.GameAnalysis import GameAnalysis
from modules.core.GameAnalysisStore import GameAnalysisStore

class RequestAnalyseReportThread(threading.Thread):
  def __init__(self, id, env):
    threading.Thread.__init__(self)
    self.id = id
    self.env = env

  def run(self):
    while True:
      logging.debug(str(self.id) + ': Getting new player ID')
      userId = self.env.api.getNextPlayerId()
      logging.debug(str(self.id) + ': Getting player data for '+userId)
      playerData = self.env.api.getPlayerData(userId)

      # pull what we already have on the player
      gameAnalysisStore = GameAnalysisStore.new()
      gameAnalysisStore.addGames(self.env.gameDB.byUserId(userId))
      gameAnalysisStore.addGameAnalyses(self.env.gameAnalysisDB.byUserId(userId))

      # Filter games and assessments for relevant info
      try:
        gameAnalysisStore.addGames([Game.fromDict(gid, userId, g) for gid, g in playerData['games'].items() if (g.get('initialFen') is None and g.get('variant') is None)])
      except KeyError:
        continue # if this doesn't gather any useful data, skip

      self.env.gameDB.lazyWriteGames(gameAnalysisStore.games)

      logging.debug(str(self.id) + ": Already Analysed: " + str(len(gameAnalysisStore.gameAnalyses)))

      gameAnalysisStore.addGameAnalyses([GameAnalysis.fromGame(game, self.env.engine, self.env.infoHandler, game.white == userId, self.env.settings['stockfish']['nodes'], self.id) for game in gameAnalysisStore.randomGamesWithoutAnalysis()])

      self.env.gameAnalysisDB.lazyWriteGameAnalyses(gameAnalysisStore.gameAnalyses)

      logging.warning(str(self.id) + ': Posting report for ' + userId)
      self.env.api.postReport(self.env.irwin.report(userId, gameAnalysisStore))

      with open('log.txt', 'a') as logfile:
        logfile.write("\n" + str(self.id) + ": Analysed " + userId)