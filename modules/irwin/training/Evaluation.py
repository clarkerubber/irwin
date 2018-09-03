from default_imports import *

from conf.ConfigWrapper import ConfigWrapper

from modules.game.Player import Player
from modules.game.GameStore import GameStore
from modules.game.AnalysedGame import GameAnalysedGame

from modules.irwin.PlayerReport import PlayerReport

class Evaluation(NamedTuple('Evaluation', [
        ('irwin', 'Irwin'),
        ('config', ConfigWrapper)
    ])):
    def getPlayerOutcomes(self, engine: bool, batchSize: int) -> Opt[int]: # returns a generator for activations, player by player.
        for player in self.irwin.env.playerDB.engineSample(engine, batchSize):
            analysedGames = self.irwin.env.analysedGameDB.byPlayerId(player.id)
            games = self.irwin.env.gameDB.byIds([ag.gameId for ag in analysedGames])
            predictions = self.irwin.analysedGameModel.predict([GameAnalysedGame(ag, g) for ag, g in zip(analysedGames, games) if ag.gameLength() <= 60])
            playerReport = PlayerReport.new(player, zip(analysedGames, predictions))
            if len(playerReport.gameReports) > 0:
                yield Evaluation.outcome(
                    playerReport.activation,
                    92, 64, engine)
            else:
                yield None

    def evaluate(self):
        outcomes = []
        [[((outcomes.append(o) if o is not None else ...), Evaluation.performance(outcomes)) for o in self.getPlayerOutcomes(engine, self.config['irwin testing eval_size'])] for engine in (True, False)]

    @staticmethod
    def performance(outcomes):
        tp = len([a for a in outcomes if a == 1])
        fn = len([a for a in outcomes if a == 2])
        tn = len([a for a in outcomes if a == 3])
        fp = len([a for a in outcomes if a == 4])
        tr = len([a for a in outcomes if a == 5])
        fr = len([a for a in outcomes if a == 6])

        cheatsLen = max(1, tp + fn + tr)
        legitsLen = max(1, fp + tn + fr)

        logging.warning("True positive: " + str(tp) + " (" + str(int(100*tp/cheatsLen)) + "%)")
        logging.warning("False negative: " + str(fn) + " (" + str(int(100*fn/cheatsLen)) + "%)")
        logging.warning("True negative: " + str(tn) + " (" + str(int(100*tn/legitsLen)) + "%)")
        logging.warning("False positive: " + str(fp) + " (" + str(int(100*fp/legitsLen)) + "%)")
        logging.warning("True Report: " + str(tr) + " (" + str(int(100*tr/cheatsLen)) + "%)")
        logging.warning("False Report: " + str(fr) + " (" + str(int(100*fr/legitsLen)) + "%)")
        logging.warning("Cheats coverage: " + str(int(100*(tp+tr)/cheatsLen)) + "%")
        logging.warning("Legits coverage: " + str(int(100*(tn)/legitsLen)) + "%")

    @staticmethod
    def outcome(a: int, tm: int, tr: int, e: bool) -> int: # activation, threshold mark, threshold report, expected value
        logging.debug(a)
        true_positive = 1
        false_negative = 2
        true_negative = 3
        false_positive = 4
        true_report = 5
        false_report = 6

        if a > tm and e:
            return true_positive
        if a > tm and not e:
            return false_positive
        if a > tr and e:
            return true_report
        if a > tr and not e:
            return false_report
        if a <= tr and e:
            return false_negative
        return true_negative