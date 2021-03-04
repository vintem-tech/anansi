"""Usefull tools for time and datetime issues."""

from typing import List

import pandas as pd
import pendulum
from pendulum.exceptions import PendulumException

from ..utils.databases.sql.schemas import DateTimeType

from ..utils.exceptions import TimeFormatError

pd.options.mode.chained_assignment = None
HUMAN_READABLE_FORMAT = "YYYY-MM-DD HH:mm:ss"


class ParseDateTime:
    """Make both way conversion timestamp/human readable datetime."""

    __slots__ = ["date_time_in"]

    def __init__(self, date_time_in: DateTimeType):
        self.date_time_in = date_time_in

    def from_human_readable_to_timestamp(self) -> int:
        """Returns an integer timestamp representation of input datetime."""

        try:
            return pendulum.from_format(
                self.date_time_in, HUMAN_READABLE_FORMAT, "UTC"
            ).int_timestamp
        except PendulumException as err:
            raise ValueError.with_traceback(err)(
                "Input datetime must be {} formatted.".format(
                    HUMAN_READABLE_FORMAT
                )
            ) from err

    def from_timestamp_to_human_readable(self) -> str:
        """Returns a string {} formatted representation of input
        timestamp""".format(
            HUMAN_READABLE_FORMAT
        )
        try:
            return pendulum.from_timestamp(
                self.date_time_in
            ).to_datetime_string()
        except PendulumException as err:
            raise ValueError.with_traceback(err)(
                "Invalid input. It must be a timestamp, integer or string type."
            ) from err


def datetime_as_integer_timestamp(datetime: DateTimeType) -> int:
    """Try to return an integer timestamp given a datetime."""

    try:
        return int(datetime)  # Already int or str timestamp (SECONDS), or ...
    except ValueError:  # ... maybe a human readable datetime, or ...
        try:
            return ParseDateTime(datetime).from_human_readable_to_timestamp()
        except ValueError as err:  # ... an invalid input.
            raise TimeFormatError.with_traceback(err)


def time_frame_to_seconds(time_frame: str) -> int:
    """Returns the equivalent amount of seconds of a given timeframe."""

    conversor = {"m": 60, "h": 3600, "d": 86400, "w": 604800}
    scale_unit = time_frame[-1]  # "m", "h", "d" or "w"
    time_amount = int(time_frame.split(scale_unit)[0])
    return time_amount * conversor[scale_unit]


def next_closed_candle_seconds_delay(
    time_frame: str, open_time: DateTimeType, **kwargs
) -> int:
    """Given a current open time and a time_frame, returns the amount
    of seconds delay between now and the next closed candle

    Args:
        time_frame (str): '5m', '2h', '1w', etc.
        open_time (DateTimeType): Current candle Open_time

    Returns:
        int: seconds delay between now and the next closed candle
    """

    _now = kwargs.get("now")

    now = (
        datetime_as_integer_timestamp(_now)
        if _now
        else pendulum.now("UTC").int_timestamp
    )

    timestamp_open_time = datetime_as_integer_timestamp(open_time)
    step = time_frame_to_seconds(time_frame)
    next_close_time = timestamp_open_time + (2 * step)
    _time_until_next_closed_candle = next_close_time - now

    if _time_until_next_closed_candle <= 0:
        _time_until_next_closed_candle = int(step / 10)

    return _time_until_next_closed_candle + 3  # A 3 sec delay
