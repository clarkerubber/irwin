from default_imports import *

from conf.ConfigWrapper import ConfigWrapper

from modules.game.Game import Game
from modules.game.Colour import Colour
from modules.game.AnalysedGame import AnalysedGame
from modules.game.EngineEval import EngineEval
from modules.game.AnalysedPosition import AnalysedPosition, AnalysedPositionDB
from modules.game.AnalysedMove import AnalysedMove, Analysis

from modules.fishnet.fishnet import stockfish_command

from chess.pgn import read_game

from chess import uci
from chess.uci import Engine
from chess.uci import InfoHandler

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from pprint import pprint

class EngineTools(NamedTuple('EngineTools', [
        ('engine', Engine),
        ('infoHandler', InfoHandler)
    ])):
    @staticmethod
    def new(conf: ConfigWrapper):
            engine = uci.popen_engine(stockfish_command(conf['stockfish update']))
            engine.setoption({'Threads': conf['stockfish threads'], 'Hash': conf['stockfish memory']})
            engine.uci()

            infoHandler = uci.InfoHandler()

            engine.info_handlers.append(infoHandler)

            return EngineTools(
                engine=engine,
                infoHandler=infoHandler)

    def analyseGame(self, game: Game, colour: Colour, nodes: int) -> Opt[AnalysedGame]:
        gameLen = len(game.pgn)
        if gameLen < 40 or gameLen > 120:
            logging.warning(f'game too long/short to analyse ({gameLen} plys)')
            return None
        elif game.emts is None:
            logging.warning(f'game has no emts')
            return None
        analysedMoves = []

        try:
            playableGame = read_game(StringIO(" ".join(game.pgn)))
        except ValueError:
            return None

        node = playableGame

        self.engine.ucinewgame()

        while not node.is_end():
            logging.info(f'analysing position\n{node.board()}\n')
            nextNode = node.variation(0)
            if colour == node.board().turn: ## if it is the turn of the player of interest
                self.engine.setoption({'multipv': 5})
                self.engine.position(node.board())
                self.engine.go(nodes=nodes)

                analyses = list([
                    Analysis(
                        pv[1][0].uci(),
                        EngineEval(engineEval[1].cp, engineEval[1].mate)) for engineEval, pv in zip(
                            self.infoHandler.info['score'].items(),
                            self.infoHandler.info['pv'].items())])

                self.engine.setoption({'multipv': 1})
                self.engine.position(nextNode.board())
                self.engine.go(nodes=nodes)

                engineEval = EngineEval(
                    self.infoHandler.info['score'][1].cp,
                    self.infoHandler.info['score'][1].mate).inverse() # flipped because analysing from other player side

                moveNumber = node.board().fullmove_number

                analysedMoves.append(AnalysedMove(
                    uci = node.variation(0).move.uci(),
                    move = moveNumber,
                    emt = game.emts[EngineTools.ply(moveNumber, colour)],
                    blur = game.getBlur(colour, moveNumber),
                    engineEval = engineEval,
                    analyses = analyses))

            node = nextNode

        playerId = game.white if colour else game.black
        return AnalysedGame.new(game.id, colour, playerId, analysedMoves)

    @staticmethod
    def ply(moveNumber, colour: Colour) -> int:
        return (2*(moveNumber-1)) + (0 if colour else 1)