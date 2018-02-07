from chess.pgn import read_game
from modules.core.PositionAnalysis import PositionAnalysis
import logging

def buildPositionAnalysisTable(env):
    logging.info("buildPositionAnalysisColl")
    logging.info("Getting GameAnalyses")
    batch = 908
    while True:
        logging.info("Processing Batch: " + str(batch))
        gameAnalyses = env.gameAnalysisDB.allBatch(batch)
        batch += 1
        if len(gameAnalyses) == 0:
            logging.info("reached end of gameAnalysisDB")
            return
        gameAnalysesLength = str(len(gameAnalyses))
        for i, gameAnalysis in enumerate(gameAnalyses):
            game = env.gameDB.byId(gameAnalysis.gameId)
            white = gameAnalysis.userId == game.white # is the player black or white
            try:
                from StringIO import StringIO
            except ImportError:
                from io import StringIO

            try:
                playableGame = read_game(StringIO(" ".join(game.pgn)))
            except ValueError:
                continue

            node = playableGame

            index = 0
            positionAnalyses = []
            logging.info("walking through game - " + game.id + " - " + str(i) + "/" + gameAnalysesLength)
            while not node.is_end():
                nextNode = node.variation(0)
                if white == node.board().turn: # if it is the turn of the player of interest
                    positionAnalyses.append(PositionAnalysis.fromBoardAndAnalyses(
                        node.board(),
                        gameAnalysis.moveAnalyses[index].analyses))
                    index += 1
                node = nextNode
            env.positionAnalysisDB.lazyWriteMany(positionAnalyses)
