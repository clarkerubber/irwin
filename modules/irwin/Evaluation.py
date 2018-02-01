import logging
from pprint import pprint

from modules.core.GameAnalysisStore import GameAnalysisStore

class Evaluation:
    def getEvaluationDataset(self, batchSize):
        print("getting players", end="...", flush=True)
        players = self.env.playerDB.balancedSample(batchSize)
        print(" %d" % len(players))
        print("getting game analyses")
        analysesByPlayer = [(player, GameAnalysisStore([], [ga for ga in self.env.gameAnalysisDB.byUserId(player.id)])) for player in players]
        return analysesByPlayer

    def evaluate(self):
        logging.warning("Evaluating Model")
        logging.debug("Getting Dataset")
        analysisStoreByPlayer = self.getEvaluationDataset(self.env.settings['irwin']['evalSize'])
        activations = [self.activation([self.gameActivation(gp, l) for gp, l in self.predictAnalysed(gameAnalysisStore.gameAnalysisTensors())]) for player, gameAnalysisStore in analysisStoreByPlayer]
        outcomes = list([(ap, Evaluation.outcome(a, 90, 60, ap[0].engine)) for ap, a in zip(analysisStoreByPlayer, activations)])
        tp = len([a for a in outcomes if a[1] == 1])
        fn = len([a for a in outcomes if a[1] == 2])
        tn = len([a for a in outcomes if a[1] == 3])
        fp = len([a for a in outcomes if a[1] == 4])
        tr = len([a for a in outcomes if a[1] == 5])
        fr = len([a for a in outcomes if a[1] == 6])

        fpnames = [a[0][0].id for a in outcomes if a[1] == 4]

        logging.warning("True positive: " + str(tp))
        logging.warning("False negative: " + str(fn))
        logging.warning("True negative: " + str(tn))
        logging.warning("False positive: " + str(fp))
        logging.warning("True Report: " + str(tr))
        logging.warning("False Report: " + str(fr))

        pprint(fpnames)

    @staticmethod
    def outcome(a, tm, tr, e): # activation, threshold, expected value
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