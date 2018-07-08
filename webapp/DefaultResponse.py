from flask import Response, json

Success = Response(
    response=json({
        'success': True,
        'message': 'action completed successfully'
        }),
    status=200,
    mimetype='application/json')

BadRequest = Response(
    response=json({
        'success': False,
        'message': 'bad request'
        }),
    status=200,
    mimetype='application/json')