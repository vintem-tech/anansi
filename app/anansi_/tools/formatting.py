"""Quis anim est incididunt anim non ullamco mollit pariatur """

import pandas as pd
from tabulate import tabulate

from .time_handlers import pendulum, seconds_in


class FormatKlines:
    """Quis anim est incididunt anim non ullamco mollit pariatur """

    __slots__ = [
        "time_frame",
        "datetime_format",
        "datetime_unit",
        "columns",
        "formatted_klines",
    ]

    def __init__(
        self,
        time_frame,
        klines: list,
        datetime_format: str,
        datetime_unit: str,
        columns: list,
    ):
        """Quis anim est incididunt anim non ullamco mollit pariatur """
        self.time_frame = time_frame
        self.datetime_format = datetime_format
        self.datetime_unit = datetime_unit
        self.columns = columns
        self.formatted_klines = [self.format_each(kline) for kline in klines]

    def format_datetime(
        self, datetime_in, truncate_seconds_to_zero=False
    ) -> int:
        """Quis anim est incididunt anim non ullamco mollit pariatur """

        if self.datetime_format == "timestamp":
            if self.datetime_unit == "seconds":
                datetime_out = int(float(datetime_in))

            elif self.datetime_unit == "milliseconds":
                datetime_out = int(float(datetime_in) / 1000)

            if truncate_seconds_to_zero:
                _date_time = pendulum.from_timestamp(int(datetime_out))

                if _date_time.second != 0:
                    datetime_out = (
                        _date_time.subtract(seconds=_date_time.second)
                    ).int_timestamp
        return datetime_out

    def format_each(self, kline: list) -> list:
        """Quis anim est incididunt anim non ullamco mollit pariatur """
        return [
            self.format_datetime(_item, truncate_seconds_to_zero=True)
            if kline.index(_item) == self.columns.index("Open_time")
            else self.format_datetime(_item)
            if kline.index(_item) == self.columns.index("Close_time")
            else float(_item)
            for _item in kline
        ]

    def to_dataframe(self) -> pd.DataFrame:
        """Quis anim est incididunt anim non ullamco mollit pariatur """
        klines = pd.DataFrame(
            self.formatted_klines, columns=self.columns
        ).astype({"Open_time": "int32", "Close_time": "int32"})

        klines.attrs.update({"SecondsTimeFrame": seconds_in(self.time_frame)})
        return klines


def table_from_dict(my_dict: dict) -> str:
    """Quis anim est incididunt anim non ullamco mollit pariatur """
    return tabulate([list(my_dict.values())], headers=list(my_dict.keys()))
