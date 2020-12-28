# pylint: disable=no-name-in-module

import json
from collections import namedtuple
from functools import partial, wraps
from time import time
import pandas as pd
import pendulum
import hashlib
from pydantic import BaseModel
from tabulate import tabulate
from ..share.schemas import TimeFormat


def short_hash_from(obj:BaseModel, length:int=8) -> str:
    return hashlib.sha256(str(obj).encode('utf-8')).hexdigest()[:length]

class ParseDateTime:
    """ Only work from/to 'YYYY-MM-DD HH:mm:ss' format """
    fmt = "YYYY-MM-DD HH:mm:ss"

    def __init__(self, date_time_in):
        self.date_time_in = date_time_in

    def from_human_readable_to_timestamp(self):
        return pendulum.from_format(
            self.date_time_in, self.fmt, "UTC"
        ).int_timestamp

    def from_timestamp_to_human_readable(self):
        return pendulum.from_timestamp(self.date_time_in).to_datetime_string()

def sanitize_input_datetime(datetime: TimeFormat) -> int:
    try:
        return int(datetime)  # Already int or str timestamp (SECONDS)
    except:  # Human readable datetime ("YYYY-MM-DD HH:mm:ss")
        try:
            return ParseDateTime(
                datetime
            ).from_human_readable_to_timestamp()
        except:
            return 0  # indicative of error


def seconds_in(time_frame: str) -> int:
    conversor_for = {"m": 60, "h": 3600, "d": 86400, "w": 604800}
    time_unit = time_frame[-1]
    time_amount = int(time_frame.split(time_unit)[0])

    return time_amount * conversor_for[time_unit]

def next_closed_candle(time_frame:str, current_open_time:str)->int:
    step = seconds_in(time_frame)
    timestamp_open_time = ParseDateTime(current_open_time).from_human_readable_to_timestamp()
    next_close_time = timestamp_open_time + (2 * step)
    return next_close_time - pendulum.now("UTC").int_timestamp + 5

class Serialize:
    def __init__(self, Target: object):
        self.Target = Target

    def to_dict(self) -> dict:
        return json.loads(
            json.dumps(self.Target, default=lambda o: o.__dict__, indent=0)
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class Deserialize:
    def __init__(self, name="X"):
        self.name = name

    def _json_object_hook(self, d):
        return namedtuple(self.name, d.keys())(*d.values())

    def from_json(self, json_in: str) -> object:
        return json.loads(json_in, object_hook=self._json_object_hook)

    def from_dict(self, dict_in: dict) -> object:
        return self.from_json(json_in=json.dumps(dict_in))


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


class DocInherit(object):
    """ Docstring inheriting method descriptor; the class itself is 
    also used as a decorator. See reference at: 
    <http://code.activestate.com/recipes/576862/>
    """

    def __init__(self, method):
        self.method = method
        self.name = method.__name__

    def __get__(self, obj, cls):
        if obj:
            return self.get_with_inst(obj, cls)
        else:
            return self.get_no_inst(cls)

    def get_with_inst(self, obj, cls):
        overridden = getattr(super(cls, obj), self.name, None)

        @wraps(self.method, assigned=("__name__", "__module__"))
        def f(*args, **kwargs):
            return self.method(obj, *args, **kwargs)

        return self.use_parent_doc(f, overridden)

    def get_no_inst(self, cls):
        for parent in cls.__mro__[1:]:
            overridden = getattr(parent, self.name, None)
            if overridden:
                break

        @wraps(self.method, assigned=("__name__", "__module__"))
        def f(*args, **kwargs):
            return self.method(*args, **kwargs)

        return self.use_parent_doc(f, overridden)

    def use_parent_doc(self, func, source):
        if source is None:
            raise NameError("Can't find {} in parents".format(self.name))
        func.__doc__ = source.__doc__
        return func


class FormatKlines:
    __slots__ = [
        "time_frame",
        "DateTimeFmt",
        "DateTimeUnit",
        "columns",
        "formatted_klines",
    ]

    def __init__(
        self,
        time_frame,
        klines: list,
        DateTimeFmt: str,
        DateTimeUnit: str,
        columns: list,
    ):
        self.time_frame = time_frame
        self.DateTimeFmt = DateTimeFmt
        self.DateTimeUnit = DateTimeUnit
        self.columns = columns
        self.formatted_klines = [self.format_each(kline) for kline in klines]

    def format_datetime(
        self, datetime_in, truncate_seconds_to_zero=False
    ) -> int:

        if self.DateTimeFmt == "timestamp":
            if self.DateTimeUnit == "seconds":
                datetime_out = int(float(datetime_in))

            elif self.DateTimeUnit == "milliseconds":
                datetime_out = int(float(datetime_in) / 1000)

            if truncate_seconds_to_zero:
                _date_time = pendulum.from_timestamp(int(datetime_out))

                if _date_time.second != 0:
                    datetime_out = (
                        _date_time.subtract(seconds=_date_time.second)
                    ).int_timestamp
        return datetime_out

    def format_each(self, kline: list) -> list:
        return [
            self.format_datetime(_item, truncate_seconds_to_zero=True)
            if kline.index(_item) == self.columns.index("Open_time")
            else self.format_datetime(_item)
            if kline.index(_item) == self.columns.index("Close_time")
            else float(_item)
            for _item in kline
        ]

    def to_dataframe(self) -> pd.DataFrame:
        klines = pd.DataFrame(
            self.formatted_klines, columns=self.columns
        ).astype({"Open_time": "int32", "Close_time": "int32"})

        klines.attrs.update({"SecondsTimeFrame": seconds_in(self.time_frame)})
        return klines


def table_from_dict(my_dict: dict) -> str:
    return tabulate([list(my_dict.values())], headers=list(my_dict.keys()))


class EventContainer:
    def __init__(self, reporter: str, description: str = None):
        self.reporter = reporter
        self.description = description
