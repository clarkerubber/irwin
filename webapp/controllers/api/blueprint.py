from flask import Blueprint, request, jsonify

def buildApiBlueprint(env, auth):
    apiBlueprint = Blueprint('Api', __name__, url_prefix='/api')

    @apiBlueprint.route('/next', methods=['GET'])
    def apiNext():
        req = request.get_json(silent=True)

        if req is not None:
            tokenId = req.get('token')

            if tokenId is not None:
                if env.auth.authoriseToken(tokenId, 'request_job'):
                    print("authorised")
        env.queue.deepPlayerQueue

    return apiBlueprint