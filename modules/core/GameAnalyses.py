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