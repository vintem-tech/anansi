"""Quis anim est incididunt anim non ullamco mollit pariatur """

# pylint: disable=no-name-in-module
# pylint: disable=too-few-public-methods

import pandas as pd
from print_dict import format_dict
from pydantic import BaseModel
from tabulate import tabulate

from .time_handlers import pendulum, time_frame_to_seconds

DF = pd.core.frame.DataFrame


def table_from_dict(my_dict: dict) -> str:
    """Quis anim est incididunt anim non ullamco mollit pariatur """

    return tabulate([list(my_dict.values())], headers=list(my_dict.keys()))


def text_in_lines_from_dict(dict_in: dict):
    """Quis anim est incididunt anim non ullamco mollit pariatur """

    return format_dict(dict_in)


class ConvertString:
    """Quis anim est incididunt anim non ullamco mollit pariatur """

    def __init__(self, string):
        self.string = string

    def from_snake_to_pascal(self):
        """Quis anim est incididunt anim non ullamco mollit pariatur """

        return (self.string.replace("_", " ").title()).replace(" ", "")


class FormatKlines:
    """Quis anim est incididunt anim non ullamco mollit pariatur """

    __slots__ = [
        "datetime_format",
        "datetime_unit",
        "columns",
        "formatted_klines",
    ]

    def __init__(self, settings: BaseModel, klines: list):
        self.datetime_format = settings.datetime_format
        self.datetime_unit = settings.datetime_unit
        self.columns = settings.kline_information
        self.formatted_klines = [self.format_each(kline) for kline in klines]

    def format_datetime(self, datetime_in, zero_truncate_seconds=False) -> int:
        """Quis anim est incididunt anim non ullamco mollit pariatur """

        if self.datetime_format == "timestamp":
            if self.datetime_unit == "seconds":
                datetime_out = int(float(datetime_in))

            elif self.datetime_unit == "milliseconds":
                datetime_out = int(float(datetime_in) / 1000)

            if zero_truncate_seconds:
                _date_time = pendulum.from_timestamp(int(datetime_out))

                if _date_time.second != 0:
                    datetime_out = (
                        _date_time.subtract(seconds=_date_time.second)
                    ).int_timestamp

        return datetime_out

    def format_each(self, kline: list) -> list:
        """Quis anim est incididunt anim non ullamco mollit pariatur """

        return [
            self.format_datetime(_item, zero_truncate_seconds=True)
            if kline.index(_item) == self.columns.index("Open_time")
            else self.format_datetime(_item)
            if kline.index(_item) == self.columns.index("Close_time")
            else float(_item)
            for _item in kline
        ]

    def to_dataframe(self) -> DF:
        """Quis anim est incididunt anim non ullamco mollit pariatur """

        klines = pd.DataFrame(
            self.formatted_klines, columns=self.columns
        ).astype({"Open_time": "int32", "Close_time": "int32"})

        return klines


def remove_last_kline_if_unclosed(klines: DF, time_frame: str) -> DF:
    """If the last candle are not yet closed, it'll be elimated.

    Args:
        klines (DataFrame): Candlesticks of the desired period Dataframe.

    Returns:
        DataFrame: Adjusted pandas Dataframe.
    """

    last_open_time = klines[-1:].Open_time.item()
    delta_time = (pendulum.now(tz="UTC")).int_timestamp - last_open_time
    unclosed = (delta_time < time_frame_to_seconds(time_frame))

    if unclosed:
        return klines[:-1]
    return klines
