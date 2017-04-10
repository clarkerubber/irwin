class AnalysedMove:
  def __init__(self, uci, moveNumber, analysis, emt):
    self.uci = uci # pgn notation for move played
    self.move = moveNumber
    self.analysis = analysis # top 4 pvs that were played
    self.emt = emt # centis spent playing move

  def __str__(self):
    return str(self.json())

  def json(self):
    return {'uci': self.uci,
      'analysis': self.analysis, # change this to something writable
      'emt': self.emt,
      'move': self.move}

def JSONToAnalysedMove(json):
  return AnalysedMove(json['uci'], json['move'], json['analysis'], json['emt'])