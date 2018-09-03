""" build and average player report and game report """
import logging
from random import shuffle
from modules.irwin.AnalysisReport import GameReportStore

def gameReportStoreByPlayers(env, players):
    logging.debug('getting player reports against players')
    playerReports = [env.playerReportDB.newestByUserId(player.id) for player in players]
    gameReports = []
    logging.debug('getting game reports against player reports')
    [gameReports.extend(env.gameReportDB.byReportId(report.id)) for report in playerReports if report is not None]
    return GameReportStore(gameReports)

def getAverages(gameReportStore):
    return {
        'averageLossByMove': gameReportStore.averageLossByMove(),
        'averageRankByMove': gameReportStore.averageRankByMove()
    }


def buildAverageReport(env):
    logging.debug('getting legit players')
    legitPlayers = env.playerDB.byEngine(False)
    titledPlayers = [player for player in legitPlayers if player.titled]

    logging.debug('---calculating legit averages---')
    legitReportStore = gameReportStoreByPlayers(env, legitPlayers)
    legitAvgs = getAverages(legitReportStore)
    del legitReportStore
    del legitPlayers

    logging.debug('---calculating titled averages---')
    titledReportStore = gameReportStoreByPlayers(env, titledPlayers)
    titledAvgs = getAverages(titledReportStore)
    del titledReportStore
    del titledPlayers

    logging.debug('---calculating engine averages---')
    engineReportStore = gameReportStoreByPlayers(env, env.playerDB.byEngine(True))
    engineAvgs = getAverages(engineReportStore)
    del engineReportStore

    averages = {
        'legit': legitAvgs,
        'titled': titledAvgs,
        'engine': engineAvgs
    }

    logging.debug(averages)
