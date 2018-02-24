from flask import Flask, render_template, url_for, redirect
from WebEnv import Env
from pprint import pprint
import json
from math import ceil

app = Flask(__name__)

config = {}
with open('conf/config.json') as confFile:
    config = json.load(confFile)
if config == {}:
    raise Exception('Config file empty or does not exist!')

env = Env(config)

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
    lightColours = ['rgba(126, 116, 214, 0.52)',
              'rgba(116, 154, 214, 0.52)',
              'rgba(116, 198, 214, 0.52)',
              'rgba(116, 214, 173, 0.52)',
              'rgba(116, 214, 121, 0.52)',
              'rgba(165, 214, 116, 0.52)',
              'rgba(203, 214, 116, 0.52)',
              'rgba(214, 190, 116, 0.52)',
              'rgba(214, 183, 116, 0.52)',
              'rgba(214, 116, 116, 0.52)']

    graphColour = lightColours[ceil(playerReport.activation/10)]

    overallActivation = ['rgba(126, 116, 214, 0.9)',
              'rgba(116, 154, 214, 0.9)',
              'rgba(116, 198, 214, 0.9)',
              'rgba(116, 214, 173, 0.9)',
              'rgba(116, 214, 121, 0.9)',
              'rgba(165, 214, 116, 0.9)',
              'rgba(203, 214, 116, 0.9)',
              'rgba(214, 190, 116, 0.9)',
              'rgba(214, 183, 116, 0.9)',
              'rgba(214, 116, 116, 0.9)'][ceil(playerReport.activation/10)]



    gameMoveActivations = [(
        gameReport.gameId,
        [move.activation for move in gameReport.moves],
        [i+1 for i in range(len(gameReport.moves))],
        [lightColours[int(move.activation/10)] for move in gameReport.moves],
        lightColours[int(gameReport.activation/10)]) for gameReport in gameReports]

    combinedLabels = list(range(max([len(gameReport.moves) for gameReport in gameReports])))

    return render_template('player-report.html',
        playerReport=playerReport,
        gameReports=gameReports,
        breakdownData=breakdownData,
        graphColour=graphColour,
        overallActivation=overallActivation,
        gameMoveActivations=gameMoveActivations,
        combinedLabels=combinedLabels)

@app.route('/game-report/<gameId>/<reportId>')
def gameReport(gameId, reportId):
    reportId = gameId + '/' + reportId
    gameReport = env.gameReportDB.byId(reportId)

    if gameReport is None:
        return ('Game report not found', 404)

    return render_template('game-report.html', gameReport=gameReport)

@app.route('/recent-reports')
def recentReports():
    playerReports = env.playerReportDB.newest()
    return render_template('recent-reports.html', playerReports=playerReports)

@app.route('/mod-reports')
def modReports():
    modReports = env.modReportDB.allOpen()
    playerReports = env.playerReportDB.byUserIds([r.id for r in modReports])

    players = list(zip(modReports, playerReports))
    players.sort(key=lambda obj: -obj[1].activation if obj[1] is not None else 150)

    return render_template('mod-reports.html', players=players)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)