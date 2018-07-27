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
        logging.info(str(authable) + ' is authorised')
        engineQueue = env.queue.nextEngineAnalysis(authable.id)
        if engineQueue is not None:
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
            logging.info(f'{authable} requested to complete job {job.playerId}')
            insertRes = env.gameApi.insertAnalysedGames(req['analysedGames'])
            if insertRes:
                env.queue.queueNerualAnalysis(job.playerId)
                env.queue.completeEngineAnalysis(job.playerId)
                return Success
        except KeyError:
            ...
        return BadRequest

    @apiBlueprint.route('/post_job', methods=['POST'])
    @env.auth.authoriseRoute(PostJob)
    def apiPostJob(authable):
        req = request.get_json(silent=True)
        try:
            games = Game.fromJson(req)
            player = Player.fromJson(req)
            origin = req['origin']

            if player is not None and len(games) > 0:
                env.playerDB.write(player)
                env.gameDB.lazyWriteMany(games)
                return Success
        except KeyError:
            ...
        return BadRequest

    return apiBlueprint