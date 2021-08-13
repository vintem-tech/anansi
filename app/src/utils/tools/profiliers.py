# pylint:disable=missing-module-docstring

from functools import wraps
from time import time


def timing(target_function):
    """Time to process some function f"""

    @wraps(target_function)
    def wrapper(*args, **kwargs):
        _start = time()
        _result = target_function(*args, **kwargs)
        print(
            "Time spent on {} method: {:6.4}s".format(
                target_function.__name__, time() - _start
            )
        )
        return _result
    return wrapper
