import logging
from modules.bcolors.bcolors import bcolors
from modules.core.AnalysedMove import Analysis, AnalysedMove, Score

def analyse(gameAnalysis, engine, infoHandler, override = False):
  if not gameAnalysis.analysed or override:
    node = gameAnalysis.playableGame

    logging.debug(bcolors.WARNING + "Game ID: " + gameAnalysis.gameId + bcolors.ENDC)
    logging.debug(bcolors.OKGREEN + "Game Length: " + str(node.end().board().fullmove_number))
    logging.debug("Analysing Game..." + bcolors.ENDC)

    engine.ucinewgame()

    analysed_positions = []

    while not node.is_end():
      nextNode = node.variation(0)
      if gameAnalysis.white == node.board().turn:
        engine.setoption({'multipv': 5})
        engine.position(node.board())
        engine.go(nodes=5000000)

        analyses = list([
          Analysis(pv[1][0].uci(),
            Score(score[1].cp, score[1].mate)) for score, pv in zip(
              infoHandler.info['score'].items(),
              infoHandler.info['pv'].items())])

        engine.setoption({'multipv': 1})
        engine.position(nextNode.board())
        engine.go(nodes=4000000)

        cp = infoHandler.info['score'][1].cp
        mate = infoHandler.info['score'][1].mate

        score = Score(-cp if cp is not None else None,
          -mate if mate is not None else None) # flipped because analysing from other player side

        moveNumber = node.board().fullmove_number

        am = AnalysedMove(
          uci = node.variation(0).move.uci(),
          move = moveNumber,
          emt = gameAnalysis.game.getEmt(gameAnalysis.ply(moveNumber)),
          score = score,
          analyses = analyses)
        gameAnalysis.analysedMoves.append(am)

      node = nextNode

    gameAnalysis.analysed = True
  return gameAnalysis