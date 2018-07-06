from default_imports import *

from modules.game.Game import Game
from modules.game.Colour import Colour
from modules.game.AnalysedGame import AnalysedGame
from modules.game.EngineEval import EngineEval
from modules.game.AnalysedPosition import AnalysedPosition, AnalysedPositionDB

from chess.pgn import read_game

from chess.uci import Engine
from chess.uci import InfoHandler

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

@validated
class EngineTools(NamedTuple('EngineTools', [
        ('engine', Engine),
        ('infoHandler', InfoHandler),
        ('analysedPositionDB', AnalysedPositionDB)
    ])):
    @staticmethod
    @validated
    def analyseGame(game: Game, colour: Colour, nodes: int) -> Opt[AnalysedGame]:
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
            if colour == node.board().turn: ## if it is the turn of the player of interest
                dbCache = self.analysedPositionDB.byBoard(node.board())
                if dbCache is not None:
                    analyses = dbCache.analyses
                else:
                    self.engine.setoption({'multipv': 5})
                    self.engine.position(node.board())
                    self.engine.go(nodes=nodes)

                    analyses = list([
                        Analysis(pv[1][0].uci(),
                            EngineEval(engineEval[1].cp, engineEval[1].mate)) for engineEval, pv in zip(
                                self.infoHandler.info['engineEval'].items(),
                                self.infoHandler.info['pv'].items())])

                    # write position to DB as it wasn't there before
                    self.analysedPositionDB.write(AnalysedPosition.fromBoardAndAnalyses(node.board(), analyses))

                dbCache = self.analysedPositionDB.byBoard(nextNode.board())
                if dbCache is not None:
                    engineEval = dbCache.analyses[0].engineEval.inverse()
                else:
                    self.engine.setoption({'multipv': 1})
                    self.engine.position(nextNode.board())
                    self.engine.go(nodes=nodes)

                    engineEval = EngineEval(self.infoHandler.info['engineEval'][1].cp,
                        self.infoHandler.info['engineEval'][1].mate).inverse() # flipped because analysing from other player side

                moveNumber = node.board().fullmove_number

                analysedMoves.append(AnalysedMove(
                    uci = node.variation(0).move.uci(),
                    move = moveNumber,
                    emt = game.emts[AnalysedGame.ply(moveNumber, colour)],
                    blur = game.getBlur(colour, moveNumber),
                    engineEval = engineEval,
                    analyses = analyses))

            node = nextNode

        userId = game.white if white else game.black
        return AnalysedGame.new(game.id, colour, userId, analysedMoves)

    @staticmethod
    @validated
    def ply(moveNumber, colour: Colour) -> int:
        return (2*(moveNumber-1)) + (0 if colour else 1)