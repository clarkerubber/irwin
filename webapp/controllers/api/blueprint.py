from flask import Blueprint, request, jsonify

def buildApiBlueprint(env):
    apiBlueprint = Blueprint('Api', __name__, url_prefix='/api')

    @apiBlueprint.route('/next', methods=['GET'])
    def apiNext():
        req = request.get_json(silent=True)

        authorised = env.auth.authoriseReq(req, 'request_job')

        if authorised:
            print('authorised')
            return env.queue.nextDeepAnalysis(authorised.id)

    return apiBlueprint