from flask import Flask, render_template, url_for, redirect
from WebEnv import Env
from pprint import pprint
import numpy as np
import json

app = Flask(__name__)

config = {}
with open('conf/config.json') as confFile:
    config = json.load(confFile)
if config == {}:
    raise Exception('Config file empty or does not exist!')

env = Env(config)

lightColours = [
          'rgba(84, 231, 96, 0.6)',
          'rgba(109, 231, 84, 0.6)',
          'rgba(131, 231, 84, 0.6)',
          'rgba(163, 231, 84, 0.6)',
          'rgba(197, 231, 84, 0.6)',
          'rgba(231, 229, 84, 0.6)',
          'rgba(231, 194, 84, 0.6)',
          'rgba(231, 158, 84, 0.6)',
          'rgba(231, 118, 84, 0.6)',
          'rgba(231, 84, 84, 0.6)']

darkColours = [
          'rgba(84, 231, 96, 0.8)',
          'rgba(109, 231, 84, 0.8)',
          'rgba(131, 231, 84, 0.8)',
          'rgba(163, 231, 84, 0.8)',
          'rgba(197, 231, 84, 0.8)',
          'rgba(231, 229, 84, 0.8)',
          'rgba(231, 194, 84, 0.8)',
          'rgba(231, 158, 84, 0.8)',
          'rgba(231, 118, 84, 0.8)',
          'rgba(231, 84, 84, 0.8)']

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/analysis-queue')
def analysisQueue():
    top = env.deepPlayerQueueDB.top(100)
    return render_template('analysis-queue.html', top=top)

@app.route('/player/<userId>')
def player(userId):
    playerObj = env.playerDB.byId(userId)
    playerReports = env.playerReportDB.byUserId(userId)
    if playerObj is None:
        return ('Player not found', 404)

    return render_template('player.html', playerObj=playerObj, playerReports=playerReports)

@app.route('/player-report/<reportId>')
def playerReport(reportId):
    playerReport = env.playerReportDB.byId(reportId)
    gameReports = env.gameReportDB.byReportId(reportId)
    gameReports.sort(key=lambda obj: -obj.activation)

    if playerReport is None:
        return ('Report not found', 404)

    breakdownData = [sum([int(gameReport.activation in range(i,i+10)) for gameReport in gameReports]) for i in range(0, 100, 10)][::-1]

    graphColour = lightColours[int(playerReport.activation/10)]

    overallActivation = darkColours[int(playerReport.activation/10)]

    lossByMove = [gameReport.losses() for gameReport in gameReports]
    longest = max([len(game) for game in lossByMove])
    lossesByMove = [[] for i in range(longest)]
    for i in range(longest):
        for game in lossByMove:
            try:
                lossesByMove[i].append(game[i])
            except IndexError:
                continue

    averageLossByMove = [np.average(move) for move in lossesByMove]

    rankByMove = [[(10 if move.rank is None else move.rank) for move in gameReport.moves] for gameReport in gameReports]
    longest = max([len(game) for game in rankByMove])
    ranksByMove = [[] for i in range(longest)]
    for i in range(longest):
        for game in rankByMove:
            try:
                ranksByMove[i].append(game[i])
            except IndexError:
                continue

    averageRankByMove = [np.average(move) for move in ranksByMove]
            
    gameMoveActivations = [(
        gameReport,
        [lightColours[int(move.activation/10)] for move in gameReport.moves],
        lightColours[int(gameReport.activation/10)],
        darkColours[int(gameReport.activation/10)],
        [('null' if move.rank is None else move.rank) for move in gameReport.moves]) for gameReport in gameReports]

    combinedLabels = list(range(1, max([len(gameReport.moves) for gameReport in gameReports])+1))

    return render_template('player-report.html',
        playerReport=playerReport,
        gameReports=gameReports,
        breakdownData=breakdownData,
        graphColour=graphColour,
        overallActivation=overallActivation,
        gameMoveActivations=gameMoveActivations,
        combinedLabels=combinedLabels,
        averageLossByMove=averageLossByMove,
        averageRankByMove=averageRankByMove)

@app.route('/game-report/<gameId>/<reportId>')
def gameReport(gameId, reportId):
    gameReportId = gameId + '/' + reportId
    playerReport = env.playerReportDB.byId(reportId)
    gameReport = env.gameReportDB.byId(gameReportId)

    if gameReport is None:
        return ('Game report not found', 404)

    game = env.gameDB.byId(gameId)
    gameAnalysis = env.gameAnalysisDB.byGameIdAndUserId(gameId, playerReport.userId)

    if game is None or gameAnalysis is None:
        return ('Game or GameAnalysis not found', 404)

    graphColor = lightColours[int(gameReport.activation/10)]
    overallActivationColor = darkColours[int(gameReport.activation/10)]
    pointColors = [darkColours[int(activation/10)] for activation in gameReport.activations()]

    seconds = gameAnalysis.emtSeconds()

    lossesByTimes = list(zip(gameAnalysis.winningChancesLossPercent(), seconds, pointColors))
    ranksByTimes = list(zip(gameAnalysis.ranks(), seconds, pointColors))
    lossesByRanks = list(zip(gameAnalysis.ranks(), gameAnalysis.winningChancesLossPercent(), pointColors))
    blursToShapes = [('rect' if blur else 'circle') for blur in gameAnalysis.blurs()]

    # Binned seconds
    emts = gameAnalysis.emts()
    steps = 10
    minSec = min(emts)
    maxSec = max(emts)
    step = int((maxSec-minSec)/steps)
    binnedSeconds = [[] for i in range(steps)]
    binnedSecondsLabels = [[] for i in range(steps)]
    for i, stepStart in enumerate(range(minSec, maxSec, step)):
        l = len([a for a in emts if a >= stepStart and a <= stepStart+step])
        binnedSeconds[min(9,i)] = l
        binnedSecondsLabels[min(9, i)] = str(int(stepStart/100)) +\
            '-' + str(int((stepStart+step)/100)) + 's'

    # Binned losses
    losses = gameAnalysis.winningChancesLossPercent()
    binnedLosses = [[] for i in range(steps)]
    binnedLossesLabels = [[] for i in range(steps)]
    for i in range(0, 20, 1):
        l = len([a for a in losses if i == int(a)])
        binnedLosses[min(9,i)] = int(100*l/len(losses))
        binnedLossesLabels[min(9, i)] = i

    # Binned pvs
    steps = 6
    pvs = gameAnalysis.ranks()
    binnedPVs = [[] for i in range(steps)]
    binnedPVsLabels = [[] for i in range(steps)]
    for i, p in enumerate([1, 2, 3, 4, 5, 'null']):
        binnedPVs[i] = len([1 for pv in pvs if pv == p])
    binnedPVsLabels = ['PV 1', 'PV 2', 'PV 3', 'PV 4', 'PV 5', 'Other']

    gameUrl = 'https://lichess.org/' + gameReport.gameId

    return render_template('game-report.html',
        gameReport=gameReport,
        game=game,
        gameAnalysis=gameAnalysis,
        playerReport=playerReport,
        overallActivationColor=overallActivationColor,
        graphColor=graphColor,
        pointColors=pointColors,
        lossesByTimes=lossesByTimes,
        ranksByTimes=ranksByTimes,
        lossesByRanks=lossesByRanks,
        gameUrl=gameUrl,
        blursToShapes=blursToShapes,
        binnedSeconds=binnedSeconds,
        binnedSecondsLabels=binnedSecondsLabels,
        binnedLosses=binnedLosses,
        binnedLossesLabels=binnedLossesLabels,
        binnedPVs=binnedPVs,
        binnedPVsLabels=binnedPVsLabels)

@app.route('/recent-reports')
def recentReports():
    playerReports = env.playerReportDB.newest()
    reportColors = [lightColours[int(playerReport.activation/10)] for playerReport in playerReports]
    reportsAndColors = list(zip(playerReports, reportColors))
    return render_template('recent-reports.html', reportsAndColors=reportsAndColors)

@app.route('/mod-reports')
def modReports():
    modReports = env.modReportDB.allOpen(300)
    playerReports = env.playerReportDB.byUserIds([r.id for r in modReports])

    players = list(zip(modReports, playerReports))
    players.sort(key=lambda obj: -obj[1].activation if obj[1] is not None else 150)

    return render_template('mod-reports.html', players=players)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)