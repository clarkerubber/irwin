""" build and average player report and game report """
import logging
from random import shuffle
from pprint import pprint
from modules.irwin.AnalysisReport import GameReportStore

def gameReportStoreByPlayers(env, players):
    playerReports = [env.playerReportDB.newestByUserId(player.id) for player in players]
    gameReports = []
    [gameReports.extend(env.gameReportDB.byReportId(report.id)) for report in playerReports if report is not None]
    return GameReportStore(gameReports)

def getAverages(gameReportStore):
    return {
        'averageLossByMove': gameReportStore.averageLossByMove(),
        'averageRankByMove': gameReportStore.averageRankByMove()
    }


def buildAverageReport(env):
    legitPlayers = env.playerDB.byEngine(False)
    titledPlayers = [player for player in legitPlayers if player.titled]

    legitReportStore = gameReportStoreByPlayers(env, legitPlayers)
    titledReportStore = gameReportStoreByPlayers(env, titledPlayers)
    engineReportStore = gameReportStoreByPlayers(env, env.playerDB.byEngine(True))

    averages = {
        'legit': getAverages(legitReportStore),
        'titled': getAverages(titledReportStore),
        'engine': getAverages(engineReportStore)
    }

    pprint(averages)
