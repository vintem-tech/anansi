"""Usefull tools for time and datetime issues."""

import pendulum

from ..utils.databases.sql.schemas import DateTimeType


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


def sanitize_input_datetime(datetime: DateTimeType) -> int:
    try:
        return int(datetime)  # Already int or str timestamp (SECONDS)
    except:  # Human readable datetime ("YYYY-MM-DD HH:mm:ss")
        try:
            return ParseDateTime(datetime).from_human_readable_to_timestamp()
        except:
            return 0  # indicative of error


def time_frame_to_seconds(time_frame: str) -> int:
    conversor_for = {"m": 60, "h": 3600, "d": 86400, "w": 604800}
    time_unit = time_frame[-1]
    time_amount = int(time_frame.split(time_unit)[0])
    return time_amount * conversor_for[time_unit]


def time_until_next_closed_candle(
    time_frame: str,
    current_open_time: str,
    now: int = pendulum.now("UTC").int_timestamp,
) -> int:
    timestamp_open_time = ParseDateTime(
        current_open_time
    ).from_human_readable_to_timestamp()

    step = time_frame_to_seconds(time_frame)
    next_close_time = timestamp_open_time + (2 * step)

    _time_until_next_closed_candle = next_close_time - now
    if _time_until_next_closed_candle <= 0:
        _time_until_next_closed_candle = int(step / 10)

    return _time_until_next_closed_candle + 5
