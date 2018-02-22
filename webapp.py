from flask import Flask, render_template, url_for, redirect
from WebEnv import Env
import json

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

    return render_template('player-report.html', playerReport=playerReport, gameReports=gameReports)

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
    players.sort(key=lambda obj: -obj[1].activation if obj[1] is not None else -150)

    return render_template('mod-reports.html', players=players)

if __name__ == '__main__':
    app.run(debug=True) 