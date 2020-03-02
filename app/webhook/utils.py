from functools import wraps

from flask import jsonify


class _BypassJSONify:
    def __init__(self, v):
        self.v = v


def jsonified_response(f):
    """decorator that automatically jsonifies return value

    use jsonified_response.bypass() or .skip() to skip jsonifying
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        r = f(*args, **kwargs)
        if isinstance(r, _BypassJSONify):
            r = r.v
        return jsonify(r)

    return wrapper


jsonified_response.bypass = jsonified_response.skip = _BypassJSONify
