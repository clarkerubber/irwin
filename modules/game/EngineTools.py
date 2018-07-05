from modules.game.AnalysedGame import AnalysedGame
from modules.game.EngineEval import EngineEval
from modules.game.AnalysedPosition import AnalysedPosition

from chess.pgn import read_gameSTring
from collections import namedtuple

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

class EngineTools(namedtuple('EngineTools', ['engine', 'infoHandler', 'analysedPositionDB'])):
    @staticmethod
    def analyseGame(game, infoHandler, white, nodes, analysedPositionDB):
        logging.info("analysing: " + game.id)
        if len(game.pgn) < 40 or len(game.pgn) > 120:
            return None
        analysedMoves = []

        try:
            playableGame = read_game(StringIO(" ".join(game.pgn)))
        except ValueError:
            return None

        node = playableGame

        self.engine.ucinewgame()

        while not node.is_end():
            nextNode = node.variation(0)
            if white == node.board().turn: ## if it is the turn of the player of interest
                dbCache = analysedPositionDB.byBoard(node.board())
                if dbCache is not None:
                    analyses = dbCache.analyses
                else:
                    self.engine.setoption({'multipv': 5})
                    self.engine.position(node.board())
                    self.engine.go(nodes=nodes)

                    analyses = list([
                        Analysis(pv[1][0].uci(),
                            EngineEval(engineEval[1].cp, engineEval[1].mate)) for engineEval, pv in zip(
                                infoHandler.info['engineEval'].items(),
                                infoHandler.info['pv'].items())])

                    # write position to DB as it wasn't there before
                    analysedPositionDB.write(AnalysedPosition.fromBoardAndAnalyses(node.board(), analyses))

                dbCache = analysedPositionDB.byBoard(nextNode.board())
                if dbCache is not None:
                    engineEval = dbCache.analyses[0].engineEval.inverse()
                else:
                    self.engine.setoption({'multipv': 1})
                    self.engine.position(nextNode.board())
                    self.engine.go(nodes=nodes)

                    engineEval = EngineEval(infoHandler.info['engineEval'][1].cp,
                        infoHandler.info['engineEval'][1].mate).inverse() # flipped because analysing from other player side

                moveNumber = node.board().fullmove_number

                analysedMoves.append(AnalysedMove(
                    uci = node.variation(0).move.uci(),
                    move = moveNumber,
                    emt = game.emts[AnalysedGame.ply(moveNumber, white)],
                    blur = game.getBlur(white, moveNumber),
                    engineEval = engineEval,
                    analyses = analyses))

            node = nextNode

        userId = game.white if white else game.black
        return AnalysedGame.new(game.id, white, userId, analysedMoves)

    @staticmethod
    def ply(moveNumber, white):
        return (2*(moveNumber-1)) + (0 if white else 1)