from modules.core.analyse import analyse

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
    bins = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0] # 10 bins representing 0-20%, 20-30%, etc...
    assessedGames = [gameAnalysis for gameAnalysis in self.gameAnalyses if gameAnalysis.moveChunkActivation is not None]
    if len(assessedGames) > 0:
      proportion = 100 / len(assessedGames)
      for assessedGame in assessedGames:
        bins[min(4, max(0, int(assessedGame.moveChunkActivation/10)))] += proportion # this is a density distribution
      bins = [int(i) for i in bins]
    return bins

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
    return len([i for i in self.gameAnalyses if i.hasHotStreak()])