from flask import Response, json

Success = Response(
    response=json.dumps({
        'success': True,
        'message': 'action completed successfully'
        }),
    status=200,
    mimetype='application/json')

BadRequest = Response(
    response=json.dumps({
        'success': False,
        'message': 'bad request'
        }),
    status=400,
    mimetype='application/json')

NotAuthorised = Response(
    response=json.dumps({
        'success': False,
        'message': 'you are not authorised to perform that action'
        }),
    status=401,
    mimetype='application/json')

NotAvailable = Response(
    response=json.dumps({
        'success': False,
        'message': 'resource not available'
        }),
    status=418,
    mimetype='application/json')