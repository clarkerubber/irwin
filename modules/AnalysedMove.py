class AnalysedMove:
  def __init__(self, board, played, analysis, emt):
    self.board = board # python-chess board
    self.played = played # pgn notation for move played
    self.analysis = analysis # top 4 pvs that were played
    self.emt = emt # centis spent playing move