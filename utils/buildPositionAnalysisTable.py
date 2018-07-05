from chess.pgn import read_game
from modules.game.AnalysedPosition import AnalysedPosition
import logging

def buildAnalysedPositionTable(env):
    logging.info("buildAnalysedPositionColl")
    logging.info("Getting AnalysedGames")
    batch = 908
    while True:
        logging.info("Processing Batch: " + str(batch))
        analysedGames = env.analysedGameDB.allBatch(batch)
        batch += 1
        if len(analysedGames) == 0:
            logging.info("reached end of analysedGameDB")
            return
        analysedGamesLength = str(len(analysedGames))
        for i, analysedGame in enumerate(analysedGames):
            game = env.gameDB.byId(analysedGame.gameId)
            white = analysedGame.userId == game.white # is the player black or white
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
            analysedPositions = []
            logging.info("walking through game - " + game.id + " - " + str(i) + "/" + analysedGamesLength)
            while not node.is_end():
                nextNode = node.variation(0)
                if white == node.board().turn: # if it is the turn of the player of interest
                    analysedPositions.append(AnalysedPosition.fromBoardAndAnalyses(
                        node.board(),
                        analysedGame.analysedMoves[index].analyses))
                    index += 1
                node = nextNode
            env.analysedPositionDB.lazyWriteMany(analysedPositions)
