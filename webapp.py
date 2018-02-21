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

@app.route('/queue')
def queue():
    top = env.deepPlayerQueueDB.top(100)
    return render_template('queue.html', top=top)

@app.route('/player/<userId>')
def player(userId):
    playerObj = env.playerDB.byId(userId)
    playerReports = env.playerReportDB.byUserId(userId)
    if playerObj is None:
        return ('Player not found', 404)

    return render_template('player.html', playerObj=playerObj, playerReports=playerReports)

if __name__ == '__main__':
    app.run(debug=True) 