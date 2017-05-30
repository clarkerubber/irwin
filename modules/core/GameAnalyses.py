from modules.core.analyse import analyse
import numpy

class GameAnalyses:
  def __init__(self, gameAnalyses):
    self.gameAnalyses = gameAnalyses

  def byGameId(self, gameId):
    return next([p for p in self.gameAnalyses if p.gameId == gameId], None)

  def append(self, gameAnalysis):
    if not self.hasId(gameAnalysis.id):
      self.gameAnalyses.append(gameAnalysis)

  def analyse(self, engine, infoHandler, nodes):
    self.gameAnalyses = [analyse(ga, engine, infoHandler, nodes) for ga in self.gameAnalyses]

  def ids(self):
    return list([ga.id for ga in self.gameAnalyses])

  def hasId(self, _id):
    return (_id in self.ids())

  def tensorInputMoves(self):
    moves = []
    [moves.extend(gameAnalysis.tensorInputMoves()) for gameAnalysis in self.gameAnalyses]
    return moves

  def tensorInputChunks(self):
    chunks = []
    [chunks.extend(gameAnalysis.tensorInputChunks()) for gameAnalysis in self.gameAnalyses]
    return chunks

  def tensorInputMoveChunks(self):
    games = []
    [games.append(gameAnalysis.tensorInputMoveChunks()) for gameAnalysis in self.gameAnalyses]
    return games

  def tensorInputPVsDraw(self): # borrowing from the PGN spy approach a little bit
    pvs = [] # all of the PV ranks for positions that match
    ts = [0, 0, 0, 0, 0] # counted PVs
    [pvs.extend(gameAnalysis.pvsDraw()) for gameAnalysis in self.gameAnalyses]
    for r in pvs:
      if r in range(1, 6):
        ts[r - 1] += 1 # Count how often each ranked PV appears
    output = [0, 0, 0, 0, 0]
    for r, t in enumerate(ts):
      output[r] = int(100 * t / max(1, len(pvs)))
    return output

  def tensorInputPVsLosing(self):
    pvs = [] # all of the PV ranks for positions that match
    ts = [0, 0, 0, 0, 0] # counted PVs
    [pvs.extend(gameAnalysis.pvsLosing()) for gameAnalysis in self.gameAnalyses]
    for r in pvs:
      if r in range(1, 6):
        ts[r - 1] += 1 # Count how often each ranked PV appears
    output = [0, 0, 0, 0, 0]
    for r, t in enumerate(ts):
      output[r] = int(100 * t / max(1, len(pvs)))
    return output

  def binnedGameActivations(self):
    bins = [0, 0, 0, 0] # 4 bins representing 90-100%, 80-100%, 50-100%, 0-50%
    brackets = [(90, 100), (80, 100), (50, 100), (0, 49)]
    activations = [gameAnalysis.activation() for gameAnalysis in self.gameAnalyses if gameAnalysis.activation() is not None]
    for i, b in enumerate(brackets):
      bins[i] = sum([a >= b[0] and a <= b[1] for a in activations])
    return bins

  def proportionalBinnedGameActivations(self):
    bins = [0, 0, 0, 0]
    bgActivations = self.binnedGameActivations()
    s = sum(bgActivations)
    if s > 0:
      for i, b in enumerate(bgActivations):
        bins[i] = int(100*b/s)
    return bins

  def averageStreaksBinned(self):
    bins = [[], [], []]
    output = [0, 0, 0]
    for gameAnalysis in self.gameAnalyses:
      if gameAnalysis.activation() > 75:
        gbins = gameAnalysis.streaksBinned()
        for i, b in enumerate(gbins):
          bins[i].append(b)
    for i in range(3):
      if len(bins[i]) > 0:
        output[i] = int(10*numpy.mean(bins[i]))
    return output

  def reportDicts(self):
    return [gameAnalysis.reportDict() for gameAnalysis in self.gameAnalyses]

  def pv0ByAmbiguityStats(self):
    totalStats = [[0, 0], [0, 0], [0, 0], [0, 0], [0, 0]] # Counter
    gameAnalysesStats = [gameAnalysis.pv0ByAmbiguityStats() for gameAnalysis in self.gameAnalyses] # Compute and store all stats
    for i in range(len(gameAnalysesStats)): # I don't like this either
      for j in range(5):
        totalStats[j][0] += gameAnalysesStats[i][j][0]
        totalStats[j][1] += gameAnalysesStats[i][j][1]
    outputStats = [0] * 5
    for i, stat in enumerate(totalStats):
      if stat[1] > 0:
        outputStats[i] = int(100 * stat[0] / stat[1]) # Convert to rate
      else:
        outputStats[i] = None
    return outputStats

  def top3average(self):
    top3 = sorted([a.activation() for a in self.gameAnalyses])[-3:]
    if len(top3) > 0:
      return numpy.mean(top3)
    return 0

  def moveActivations(self):
    activations = []
    [activations.extend(gameAnalysis.moveActivations()) for gameAnalysis in self.gameAnalyses]
    return activations

  def chunkActivations(self):
    activations = []
    [activations.extend(gameAnalysis.chunkActivations()) for gameAnalysis in self.gameAnalyses]
    return activations

  def gameActivations(self):
    return [gameAnalysis.moveChunkActivation for gameAnalysis in self.gameAnalyses if gameAnalysis.moveChunkActivation is not None]

  def gamesWithHotStreaks(self):
    return len([i for i in self.gameAnalyses if i.maxStreak(80) > 5])