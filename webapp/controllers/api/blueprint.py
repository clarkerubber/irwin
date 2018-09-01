import logging
from flask import Blueprint, Response, request, jsonify, json
from webapp.DefaultResponse import Success, BadRequest, NotAvailable

from modules.game.Game import Game
from modules.game.Player import Player
from modules.auth.Priv import RequestJob, CompleteJob, PostJob
from modules.queue.Origin import OriginReport, OriginModerator, OriginRandom
from modules.client.Job import Job

def buildApiBlueprint(env):
    apiBlueprint = Blueprint('Api', __name__, url_prefix='/api')

    @apiBlueprint.route('/request_job', methods=['GET'])
    @env.auth.authoriseRoute(RequestJob)
    def apiRequestJob(authable):
        engineQueue = env.queue.nextEngineAnalysis(authable.id)
        if engineQueue is not None:
            games = env.gameEnv
            job = Job(engineQueue.id, env.gameEnv.gameDB.byPlayerId(engineQueue.id), [])
            return  Response(
                response=json.dumps(job.toJson()),
                status=200,
                mimetype='application/json')
        return NotAvailable

    @apiBlueprint.route('/complete_job', methods=['POST'])
    @env.auth.authoriseRoute(CompleteJob)
    def apiCompleteJob(authable):
        req = request.get_json(silent=True)
        try:
            job = Job.fromJson(req['job'])
            insertRes = env.gameApi.insertAnalysedGames(req['analysedGames'])
            if insertRes:
                env.queue.queueNerualAnalysis(job.playerId)
                env.queue.completeEngineAnalysis(job.playerId)
                return Success
        except KeyError:
            ...
        return BadRequest

    return apiBlueprint