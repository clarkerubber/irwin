from collections import namedtuple
import numpy as np
import math
from pprint import pprint

class GameAnalysisStore(namedtuple('GameAnalysisStore', ['games', 'gameAnalyses'])):
  def gamesWithoutAnalysis(self, excludeIds=[]):
    return [game for game in self.games if not self.gameIdHasAnalysis(game.id) if (game.id not in excludeIds)]

  def gameIdHasAnalysis(self, gid):
    return any([ga for ga in self.gameAnalyses if ga.gameId == gid])

  def hasGameId(self, gid):
    return any([g for g in self.games if gid == g.id])

  def gameById(self, gid):
    return next(iter([g for g in self.games if gid == g.id]), None)

  def addGames(self, games):
    [self.games.append(g) for g in games if (not self.hasGameId(g.id) and g.emts is not None and len(g.pgn) < 120 and len(g.pgn) > 40)]

  def addGameAnalyses(self, gameAnalyses):
    [self.gameAnalyses.append(ga) for ga in gameAnalyses if not self.gameIdHasAnalysis(ga.gameId) and ga is not None and len(ga.moveAnalyses) < 60 and len(ga.moveAnalyses) > 20]

  def randomGamesWithoutAnalysis(self, size = 10, excludeIds=[]):
    gWithout = self.gamesWithoutAnalysis(excludeIds)
    if len(gWithout) > 0:
      return [gWithout[x] for x in np.random.choice(list(range(len(gWithout))), min(len(gWithout), size), replace=False)]
    return []

  def gameTensors(self, userId):
    tensors = [(g.id, g.tensor(userId)) for g in self.games]
    return [t for t in tensors if t[1] is not None]

  def gameTensorsWithoutAnalysis(self, userId):
    return [(gid, t) for gid, t in self.gameTensors(userId) if not self.gameIdHasAnalysis(gid)]

  def gameAnalysisTensors(self):
    return [gameAnalysis.moveAnalysisTensors() for gameAnalysis in self.gameAnalyses if len(gameAnalysis.moveAnalyses) < 60 and len(gameAnalysis.moveAnalyses) > 20]

  def quickGameAnalysisTensors(self):
    self.awclByWinningChances()
    return [gameAnalysis.moveAnalysisTensors() for gameAnalysis in self.gameAnalyses if len(gameAnalysis.moveAnalyses) < 60 and len(gameAnalysis.moveAnalyses) > 20 and gameAnalysis.emtAverage() < 2000]

  def quickGameAnalyses(self):
    return [gameAnalysis for gameAnalysis in self.gameAnalyses if gameAnalysis.emtAverage() < 2000]

  def playerTensor(self):
    return self.awclByEmt()+self.awclByPhase()+self.awclByWinningChances()

  def awclByEmt(self):
    bins = [(0, 50), (50, 100), (100, 200), (200, 400), (400, 600), (600, math.inf)]
    wclByEmts = [ga.wclByEmt() for ga in self.gameAnalyses]
    exWclByEmts = []
    [exWclByEmts.extend(wbe) for wbe in wclByEmts]
    binned = [[wcl for emt, wcl in exWclByEmts if emt > l and emt <= h] for l, h in bins]
    avgBins = [self.negIfNan(np.average(b)) for b in binned]
    return avgBins

  def awclByPhase(self):
    bins = [(0, 5), (5, 10), (10, 15), (15, 20), (25, 30), (30, math.inf)]
    wclByMoveNumbers = [ga.wclByMoveNumber() for ga in self.gameAnalyses]
    exWclByMoveNumbers = []
    [exWclByMoveNumbers.extend(wbe) for wbe in wclByMoveNumbers]
    binned = [[wcl for mn, wcl in exWclByMoveNumbers if mn > l and mn <= h] for l, h in bins]
    avgBins = [self.negIfNan(np.average(b)) for b in binned]
    return avgBins

  def awclByWinningChances(self):
    bins = [(0, 10), (10, 20), (20, 30), (30, 40), (40, 50), (50, 60), (60, 70), (70, 80), (80, 90), (90, 100)]
    wclByWinningChances = [ga.wclByWinningChances() for ga in self.gameAnalyses]
    exWclByWinningChances = []
    [exWclByWinningChances.extend(wbe) for wbe in wclByWinningChances]
    binned = [[wcl for wc, wcl in exWclByWinningChances if wc*100 > l and wc*100 <= h] for l, h in bins]
    avgBins = [self.negIfNan(np.average(b)) for b in binned]
    return avgBins

  @staticmethod
  def negIfNan(n, mul=1000):
    return (-1 if np.isnan(n) else mul*n)

  @staticmethod
  def new():
    return GameAnalysisStore([], [])