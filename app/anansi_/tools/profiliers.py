from functools import wraps
from time import time


def timing(f):
    """Time to process some function f"""

    @wraps(f)
    def wrapper(*args, **kwargs):
        _start = time()
        _result = f(*args, **kwargs)
        print(
            "Time spent on {} method: {:6.4}s".format(
                f.__name__, time() - _start
            )
        )
        return _result
    return wrapper
