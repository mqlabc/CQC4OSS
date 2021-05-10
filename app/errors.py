from werkzeug.http import HTTP_STATUS_CODES


def api_message(http_code, code=None, message=None, data=None, **kwargs):
    if message is None:
        message = HTTP_STATUS_CODES.get(http_code, '')
    if data is None:
        response = dict(code=code, message=message, **kwargs)
    else:
        response = dict(code=code, message=message, data=data, **kwargs)
    return response, http_code


def my_auth_error(status):
    return api_message(200, 1001, 'invalid token, maybe your login is outdated')
