from modules.AnalysedMove import AnalysedMove

class GameAnalysis:
  def __init__(self, game, playerAssessment):
    try:
      from StringIO import StringIO
    except ImportError:
      from io import StringIO
    self.game = game
    self.playerAssessment = playerAssessment
    self.analysed = False
    self.playableGame = chess.pgn.read_game(StringIO(game.pgn))
    self.analysedMoves = [] # List[AnalysedMove]

  def __str__(self):
    return str(self.game) + "\n" + str(self.playerAssessment)

  def analyse(self, engine, infoHandler):
    node = self.playableGame

    logging.debug(bcolors.WARNING + "Game ID: " + self.assessment.gameId + bcolors.ENDC)
    logging.debug(bcolors.OKGREEN + "Game Length: " + str(node.end().board().fullmove_number))
    logging.debug("Analysing Game..." + bcolors.ENDC)

    engine.ucinewgame()

    analysed_positions = []

    while not node.is_end():
      nextNode = node.variation(0)
      engine.position(nextNode.board())

      if self.game.white == node.board().turn:
        #AnalysedMove(node.board().copy(), )
        analysed_legals = []

        for p in node.board().legal_moves:
          position_copy = node.board().copy()
          position_copy.push(p)
          engine.position(position_copy)
          engine.go(nodes=800000)
          analysed_legals.append(AnalysedMove(p, infoHandler.info["score"][1]))

        analysed_legals = sorted(analysed_legals, key=methodcaller('sort_val'))
        played_move = next((x for x in analysed_legals if x.move == nextNode.move), None)
        analysed_positions.append(AnalysedPosition(played_move, analysed_legals))

      node = nextNode

    self.analysed = AnalysedGame(self.assessment, analysed_positions)

  def userId(self):
    return self.playerAssessment.userId

  def gameId(self):
    return self.game.id