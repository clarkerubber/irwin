import logging
from flask import Blueprint, request, jsonify, json
from webapp import DefaultResponse

from modules.game.Player import Player, Game
from modules.auth.Priv import RequestJob, CompleteJob, PostJob
from modules.queue.Origin import OriginReport, OriginModerator, OriginRandom

def buildApiBlueprint(env):
    apiBlueprint = Blueprint('Api', __name__, url_prefix='/api')

    @apiBlueprint.route('/request_job', methods=['GET'])
    def apiRequestJob():
        req = request.get_json(silent=True)

        authable, authorised = env.auth.authoriseReq(req, RequestJob)

        if authorised:
            logging.info(str(authable) + ' is authorised')
            return env.queue.nextDeepAnalysis(authable.id)

    @apiBlueprint.route('/complete_job', methods=['POST'])
    def apiCompleteJob():
        req = request.get_json(silent=True)

        authable, authorised = env.auth.authoriseReq(req, CompleteJob)

        if authorised:
            analysisId = req.get('id')
            logging.info(str(authable) + ' requested to complete job ' + analysisId)
            if analysisId is not None:
                env.gameApi.insertAnalysedGames(req.get('game_analyses'))
                env.queue.queueNerualAnalysis(analysisId)
                env.queue.completeEngineAnalysis(analysisId)
                return DefaultResponse.Success
        return DefaultResponse.BadRequest

    @apiBlueprint.route('/post_job', methods=['POST'])
    def apiPostJob():
        req = request.get_json(silent=True)

        authable, authorised = env.auth.authoriseReq(req, PostJob)

        if authorised:
            games = Game.fromJson(req)
            player = Player.fromJson(req)
            origin = req.get('origin')

            if None not in [player, origin] and len(games) > 0:
                env.playerDB.write(player)
                env.gameDB.lazyWriteMany(games)
            else:
                return DefaultResponse.BadRequest