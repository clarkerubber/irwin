from modules.core.analyse import analyse

class GameAnalyses:
  def __init__(self, gameAnalyses):
    self.gameAnalyses = gameAnalyses

  def byGameId(self, gameId):
    return next([p for p in self.gameAnalyses if p.gameId == gameId], None)

  def append(self, gameAnalysis):
    if not self.hasId(gameAnalysis.id):
      self.gameAnalyses.append(gameAnalysis)

  def analyse(self, engine, infoHandler):
    self.gameAnalyses = [analyse(ga, engine, infoHandler) for ga in self.gameAnalyses]

  def ids(self):
    return list([ga.id for ga in self.gameAnalyses])

  def hasId(self, _id):
    return (_id in self.ids())

  def tensorInputMoves(self, titled):
    moves = []
    [moves.extend(gameAnalysis.tensorInputMoves(titled)) for gameAnalysis in self.gameAnalyses]
    return moves

  def tensorInputChunks(self, titled):
    chunks = []
    [chunks.extend(gameAnalysis.tensorInputChunks(titled)) for gameAnalysis in self.gameAnalyses]
    return chunks

  def assessmentNoOutlierAverages(self):
    return [gameAnalysis.assessmentNoOutlierAverage() for gameAnalysis in self.gameAnalyses]

  def reportDicts(self):
    return [gameAnalysis.reportDict() for gameAnalysis in self.gameAnalyses]

  def pv0ByAmbiguityStats(self):
    totalStats = [[0, 0], [0, 0], [0, 0], [0, 0], [0, 0]] # Counter
    gameAnalysesStats = [gameAnalysis.pv0ByAmbiguityStats() for gameAnalysis in self.gameAnalyses] # Compute and store all stats
    for i in range(len(gameAnalysesStats)): # I don't like this either
      for j in range(5):
        totalStats[j][0] = totalStats[j][0] + gameAnalysesStats[i][j][0]
        totalStats[j][1] = totalStats[j][1] + gameAnalysesStats[i][j][1]
    outputStats = [0] * 5
    for i, stat in enumerate(totalStats):
      if stat[1] > 0:
        outputStats[i] = int(100 * stat[0] / stat[1]) # Convert to rate
      else:
        outputStats[i] = None
    return outputStats