import logging
from pprint import pprint

from modules.game.GameStore import GameStore

class Evaluation:
    def getEvaluationDataset(self, batchSize):
        print("getting players", end="...", flush=True)
        players = self.env.playerDB.balancedSample(batchSize)
        print(" %d" % len(players))
        print("getting game analyses")
        analysesByPlayer = [(player, GameStore([], [ga for ga in self.env.analysedGameDB.byPlayerId(player.id)])) for player in players]
        return analysesByPlayer

    def evaluate(self):
        logging.warning("Evaluating Model")
        logging.debug("Getting Dataset")
        analysisStoreByPlayer = self.getEvaluationDataset(self.env.config['irwin']['evalSize'])
        activations = [self.activation(player, [self.gameActivation(gp, l) for gp, l in self.predictAnalysed(gameStore.analysedGameTensors())]) for player, gameStore in analysisStoreByPlayer]
        outcomes = list([(ap, Evaluation.outcome(a, 92, 64, ap[0].engine)) for ap, a in zip(analysisStoreByPlayer, activations)])
        tp = len([a for a in outcomes if a[1] == 1])
        fn = len([a for a in outcomes if a[1] == 2])
        tn = len([a for a in outcomes if a[1] == 3])
        fp = len([a for a in outcomes if a[1] == 4])
        tr = len([a for a in outcomes if a[1] == 5])
        fr = len([a for a in outcomes if a[1] == 6])

        fpnames = [a[0][0].id for a in outcomes if a[1] == 4]

        cheatsLen = tp + fn + tr
        legitsLen = fp + tn + fr 

        logging.warning("True positive: " + str(tp) + " (" + str(int(100*tp/cheatsLen)) + "%)")
        logging.warning("False negative: " + str(fn) + " (" + str(int(100*fn/cheatsLen)) + "%)")
        logging.warning("True negative: " + str(tn) + " (" + str(int(100*tn/legitsLen)) + "%)")
        logging.warning("False positive: " + str(fp) + " (" + str(int(100*fp/legitsLen)) + "%)")
        logging.warning("True Report: " + str(tr) + " (" + str(int(100*tr/cheatsLen)) + "%)")
        logging.warning("False Report: " + str(fr) + " (" + str(int(100*fr/legitsLen)) + "%)")
        logging.warning("Cheats coverage: " + str(int(100*(tp+tr)/cheatsLen)) + "%")
        logging.warning("Legits coverage: " + str(int(100*(tn)/legitsLen)) + "%")

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