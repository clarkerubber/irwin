from flask import Flask, render_template, url_for, redirect, request, jsonify
from WebEnv import Env
from pprint import pprint
import numpy as np
from math import log10, floor
import json

from modules.game.Player import Player

from modules.game.GameAnalysisStore import GameAnalysisStore

from modules.irwin.AnalysisReport import GameReportStore

from modules.irwin.GameBasicActivation import GameBasicActivation

from modules.queue.DeepPlayerQueue import DeepPlayerQueue
from modules.queue.ModReport import ModReport

app = Flask(__name__)

config = {}
with open('conf/config.json') as confFile:
    config = json.load(confFile)
if config == {}:
    raise Exception('Config file empty or does not exist!')

env = Env(config)

darkColors = [
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

def round_sig(x, sig=2):
    if x == 0:
        return 0
    return round(x, sig-int(floor(log10(abs(x))))-1)

@app.route('/')
@app.route('/watchlist')
def watchlist():
    playerReports = env.playerReportDB.newest(1000)
    players = env.playerDB.unmarkedByUserIds([playerReport.userId for playerReport in playerReports]) # player = None if engine
    playersWithReports = [(player, report, darkColors[int(report.activation/10)]) for player, report in zip(players, playerReports) if player is not None]

    uniquePlayersWithReports = []
    alreadyAdded = []
    for player, report, color in playersWithReports:
        if player.id not in alreadyAdded and report.activation > 70:
            uniquePlayersWithReports.append((player, report, color))
            alreadyAdded.append(player.id)

    uniquePlayersWithReports.sort(key=lambda obj: -obj[1].activation) # sort by report activation

    return render_template('watchlist.html',
        playersWithReports=uniquePlayersWithReports)

@app.route('/recent-reports')
def recentReports():
    playerReports = env.playerReportDB.newest()
    reportColors = [darkColors[int(playerReport.activation/10)] for playerReport in playerReports]
    reportsAndColors = list(zip(playerReports, reportColors))
    return render_template('recent-reports.html', reportsAndColors=reportsAndColors)

@app.route('/analysis-queue')
def analysisQueue():
    top = env.deepPlayerQueueDB.top(100)
    return render_template('analysis-queue.html', top=top)

@app.route('/mod-reports/<page>')
def modReports(page):
    if page not in ['top', 'bottom']:
        return ('Page not found', 404)

    reports = env.modReportDB.allOpen(500)

    reportsWithAnalysis = [(report, env.playerReportDB.newestByUserId(report.id)) for report in reports]
    reportsWithAnalysis = [(modReport, irwinReport, darkColors[int(irwinReport.activation/10)]) for modReport, irwinReport in reportsWithAnalysis if irwinReport is not None]

    multiplier = -1 if page == 'top' else 1
    reportsWithAnalysis.sort(key=lambda obj: multiplier * obj[1].activation)

    return render_template('mod-reports.html',
        reportsWithAnalysis=reportsWithAnalysis[:50],
        title=page)

@app.route('/player/<userId>')
def player(userId):
    playerObj = env.playerDB.byId(userId)
    if playerObj is None:
        return ('Player not found', 404)

    playerReports = env.playerReportDB.byUserId(userId)
    colors = [darkColors[int(report.activation/10)] for report in playerReports]
    reportsWithColors = list(zip(playerReports, colors))

    availableGames = env.gameBasicActivationDB.byUserId(userId)
    availableGames.sort(key=lambda obj: -obj.prediction)

    deepPlayerQueue = env.deepPlayerQueueDB.byId(userId)

    reportOpen = env.modReportDB.isOpen(userId)

    return render_template(
        'player.html',
        playerObj=playerObj,
        reportsWithColors=reportsWithColors,
        availableGames=availableGames,
        deepPlayerQueue=deepPlayerQueue,
        reportOpen=reportOpen)

@app.route('/player-report/<reportId>')
def playerReport(reportId):
    playerReport = env.playerReportDB.byId(reportId)
    gameReports = env.gameReportDB.byReportId(reportId)
    gameReports.sort(key=lambda obj: -obj.activation)
    gameReportStore = GameReportStore(gameReports)

    if playerReport is None:
        return ('Report not found', 404)

    overallActivationColor = darkColors[int(playerReport.activation/10)]
            
    combinedLabels = list(range(1, gameReportStore.longestGame()+1))

    return render_template('player-report.html',
        playerReport=playerReport,
        overallActivationColor=overallActivationColor,
        combinedLabels=combinedLabels,
        gameReportStore=gameReportStore,
        darkColors=darkColors)

@app.route('/game-report/<reportId>/<gameId>')
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

    graphColor = darkColors[int(gameReport.activation/10)]
    pointColors = [darkColors[int(activation/10)] for activation in gameReport.activations()]

    gameUrl = 'https://lichess.org/' + gameReport.gameId

    return render_template('game-report.html',
        gameReport=gameReport,
        game=game,
        gameAnalysis=gameAnalysis,
        playerReport=playerReport,
        graphColor=graphColor,
        pointColors=pointColors,
        gameUrl=gameUrl)

@app.route('/api/update-player-data', methods=['GET', 'POST'])
def updatePlayerData():
    content = request.json
    userId = content['userId']
    print("updating player " + userId)
    player = Player.fromPlayerData(env.api.getPlayerData(userId))
    if player is not None:
        env.playerDB.write(player)
        if player.reportScore is None:
            env.modReportDB.close(player.id)
        else:
            env.modReportDB.create(ModReport.new(player.id))
        print("updated player!")
    else:
        print("failed!")
        return "{'updated': false}", 204

    gameAnalysisStore = GameAnalysisStore.new()
    gameAnalysisStore.addGames(env.gameDB.byUserIdAnalysed(userId))
    gameTensors = gameAnalysisStore.gameTensors(userId)

    if len(gameTensors) > 0:
        gamePredictions = env.irwin.predictBasicGames(gameTensors)
        gameActivations = [GameBasicActivation.fromPrediction(gameId, userId, prediction, False)
            for gameId, prediction in gamePredictions]
        env.gameBasicActivationDB.lazyWriteMany(gameActivations)
    print("updated games!")
    return "{'updated': true}", 201
    
@app.route('/api/mark-game', methods=['GET', 'POST'])
def markGameForAnalysis():
    content = request.json
    userId = content['userId']
    gameId = content['gameId']
    print("marking for analysis " + gameId + '/' + userId)
    player = env.playerDB.byId(userId)

    if player is not None:
        player.mustAnalyse.append(gameId)
        env.playerDB.write(player)
        return "{'updated': true}", 201
    else:
        return "{'updated': false}", 204

@app.route('/api/analyse-player', methods=['GET', 'POST'])
def analysePlayer():
    content = request.json
    userId = content['userId']
    print("queing player for analysis " + userId)
    player = env.playerDB.byId(userId)

    if player is not None:
        env.deepPlayerQueueDB.write(DeepPlayerQueue.new(
            userId=userId,
            origin='moderator',
            gamePredictions=[]))
        return "{'queued': true}", 201
    else:
        return "{'queued': false}", 204

@app.route('/api/close-mod-report', methods=['GET', 'POST'])
def closeModReport():
    content = request.json
    userId = content['userId']
    print("closing reports for " + userId)
    env.modReportDB.close(userId)
    return "{'queued': true}", 201
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)