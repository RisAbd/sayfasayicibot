from functools import wraps

from flask import jsonify


class IgnoreJSONify(BaseException):
    pass


def jsonified_response(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return jsonify(f(*args, **kwargs))
        except IgnoreJSONify as e:
            return e.args[0]

    return wrapper


jsonified_response.Ignore = IgnoreJSONify
