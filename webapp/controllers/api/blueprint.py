import logging
from flask import Blueprint, Response, request, jsonify, json
from webapp.DefaultResponse import Success, BadRequest, NotAvailable

from modules.game.AnalysedGame import GameAnalysedGame
from modules.irwin.PlayerReport import PlayerReport
from modules.auth.Priv import RequestJob, CompleteJob, PostJob
from modules.queue.Origin import OriginReport, OriginModerator, OriginRandom
from modules.client.Job import Job

def buildApiBlueprint(env):
    apiBlueprint = Blueprint('Api', __name__, url_prefix='/api')

    @apiBlueprint.route('/request_job', methods=['GET'])
    @env.auth.authoriseRoute(RequestJob)
    def apiRequestJob(authable):
        engineQueue = env.queue.nextEngineAnalysis(authable.id)
        logging.debug(f'EngineQueue for req {engineQueue}')
        if engineQueue is not None:
            games = env.gameApi.gamesForAnalysis(
                playerId = engineQueue.id,
                required = engineQueue.requiredGameIds)

            basicGamePredictions = env.irwin.basicGameModel.predict(
                playerId = engineQueue.id ,
                games = games)

            logging.debug(str(basicGamePredictions))

            topGames = sorted(
                [(g, p) for g, p in zip(games, basicGamePredictions) if p is not None],
                key=lambda x: x[1],
                reverse=True)[:10]

            topGames = [g for g, p in topGames]
            requiredGames = [g for g in games if g.id in engineQueue.requiredGameIds]

            gamesToAnalyse = topGames + requiredGames

            gameIds = [g.id for g in gamesToAnalyse]

            logging.info(f'Requesting {authable.id} analyses {gameIds} for {engineQueue.id}')

            job = Job(
                playerId = engineQueue.id,
                games = gamesToAnalyse,
                analysedPositions = [])

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

                env.lichessApi.postReport(playerReport)

                return Success
        except KeyError:
            ...
        return BadRequest

    return apiBlueprint