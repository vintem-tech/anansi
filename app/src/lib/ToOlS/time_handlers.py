"""Usefull tools for time and datetime issues."""

import math
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


@pd.api.extensions.register_dataframe_accessor("apply_datetime_conversion")
class DataFrameDateTimeconversion:
    """Apply timestamp/human readable datetime conversion over
    dataframe columns items."""

    __slots__ = ["_dataframe"]

    def __init__(self, dataframe: pd.core.frame.DataFrame):
        self._dataframe = dataframe

    def _convert(self, column: str, conversion: str) -> None:
        self._dataframe.loc[:, column] = self._dataframe.apply(
            lambda func: getattr(ParseDateTime(func[column]), conversion)(),
            axis=1,
        )

    def from_human_readable_to_timestamp(self, target_columns: List[str]):
        """If human readable str, returns associated int timestamp."""

        for column in target_columns:
            self._convert(column, "from_human_readable_to_timestamp")

    def from_timestamp_to_human_readable(self, target_columns: List[str]):
        """If int timestamp, returns associated human readable str."""

        for column in target_columns:
            self._convert(column, "from_timestamp_to_human_readable")


def datetime_as_integer_timestamp(datetime: DateTimeType) -> int:
    """Try to return an integer timestamp given a datetime."""

    try: # Already int or str timestamp (SECONDS), or ...
        return int(datetime)
    except ValueError:
        try:  # ... maybe a human readable datetime, or ...
            return ParseDateTime(datetime).from_human_readable_to_timestamp()
        except ValueError as err:  # ... an invalid input.
            raise TimeFormatError.with_traceback(err)


def time_frame_to_seconds(time_frame: str) -> int:
    """Returns the equivalent amount of seconds of a given timeframe."""

    conversor = {"m": 60, "h": 3600, "d": 86400, "w": 604800}
    scale_unit = time_frame[-1]  # "m", "h", "d" or "w"
    time_amount = int(time_frame.split(scale_unit)[0])
    return time_amount * conversor[scale_unit]

def cooldown_time(attempt:int, max_cooldown_time="1h"):
    """Returns a cooldown time which is exponentially depending to
    the number of attempts and rises asymptotically to the defined
    max_cooldown_time.

    Args:
        attempt ([type]): Index of the attempt('round').
        max_cooldown_time (str, optional): like timestamp
        <amount><scale_unit> e.g. '1m', '2h'. Defaults to "1h".

    Returns:
        [type]: [description]
    """
    time_0 = 2 # To seconds minimum cooldown time
    max_time = time_frame_to_seconds(max_cooldown_time)
    ref = 1000 # attempt index that implies t = ~0.63*max_cooldown_time
    power = -((attempt - 1)/ref)
    return int(max_time*(1 - math.exp(power)) + time_0)

def next_closed_candle_seconds_delay(
    time_frame: str, open_time: DateTimeType, **kwargs
) -> int:
    """Given a current open time and a time_frame, returns the amount
    of seconds delay between now and the next closed candle.

    Args:
        time_frame (str): <amount><scale_unit> e.g. '1m', '2h'
        open_time (DateTimeType): Current candle Open_time

    Returns:
        int: seconds delay between now and the next closed candle
    """

    now = kwargs.get("now", pendulum.now("UTC").int_timestamp)

    timestamp_open_time = datetime_as_integer_timestamp(open_time)
    step = time_frame_to_seconds(time_frame)
    next_close_time = timestamp_open_time + (2 * step)
    _time_until_next_closed_candle = next_close_time - now

    return (_time_until_next_closed_candle + 3  # A 3 sec delay
    if _time_until_next_closed_candle <= 0
    else int(step / 10)
    )
