import logging
from flask import Blueprint, Response, request, jsonify, json
from webapp.DefaultResponse import Success, BadRequest, NotAvailable

from modules.game.AnalysedGame import GameAnalysedGame
from modules.irwin.PlayerReport import PlayerReport
from modules.auth.Priv import RequestJob, CompleteJob, PostJob
from modules.queue.Origin import OriginReport, OriginModerator, OriginRandom
from modules.client.Job import Job
import traceback

def buildApiBlueprint(env):
    apiBlueprint = Blueprint('Api', __name__, url_prefix='/api')

    @apiBlueprint.route('/request_job', methods=['GET'])
    @env.auth.authoriseRoute(RequestJob)
    def apiRequestJob(authable):
        engineQueue = env.queue.nextEngineAnalysis(authable.id)
        logging.debug(f'EngineQueue for req {engineQueue}')
        if engineQueue is not None:
            requiredGames = env.gameApi.gamesForAnalysis(engineQueue.playerId)
            requiredGameIds = [g.id for g in requiredGames]

            logging.warning(f'Requesting {authable.name} analyses {requiredGameIds} for {engineQueue.id}')

            job = Job(
                playerId = engineQueue.id,
                games = requiredGames,
                analysedPositions = [])

            logging.info(f'Job: {job}')

            return  Response(
                response = json.dumps(job.toJson()),
                status = 200,
                mimetype = 'application/json')
        return NotAvailable

    @apiBlueprint.route('/complete_job', methods=['POST'])
    @env.auth.authoriseRoute(CompleteJob)
    def apiCompleteJob(authable):
        req = request.get_json(silent=True)
        try:
            job = Job.fromJson(req['job'])
            insertRes = env.gameApi.writeAnalysedGames(req['analysedGames'])
            if insertRes:
                env.queue.completeEngineAnalysis(job.playerId)

                player = env.irwin.env.playerDB.byId(job.playerId)
                analysedGames = env.irwin.env.analysedGameDB.byPlayerId(job.playerId)
                games = env.irwin.env.gameDB.byIds([ag.gameId for ag in analysedGames])
                predictions = env.irwin.analysedGameModel.predict([GameAnalysedGame(ag, g) for ag, g in zip(analysedGames, games) if ag.gameLength() <= 60])

                playerReport = PlayerReport.new(player, zip(analysedGames, predictions), owner = authable.name)
                logging.warning(f'Sending player report for {playerReport.playerId}, activation {playerReport.activation}%')
                env.lichessApi.postReport(playerReport)

                return Success
        except KeyError as e:
            tb = traceback.format_exc()
            logging.warning(f'Error completing job: {tb}')

        return BadRequest

    return apiBlueprint
