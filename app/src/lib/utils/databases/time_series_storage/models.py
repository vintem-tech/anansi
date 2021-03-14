import pandas as pd

from ....tools.time_handlers import time_frame_to_seconds
from .engines import InfluxDbV1 as InfluxDb


class StorageKlines:
    __slots__ = [
        "table",
        "database",
        "time_frame",
        "engine",
        "_oldest_open_time",
        "_newest_open_time",
    ]

    def __init__(self, table: str, time_frame: str):
        self.database = "klines"
        self.table = table
        self.time_frame = time_frame
        self.engine = InfluxDb(self.database, table)
        self._oldest_open_time = self.engine.oldest().Timestamp.item()
        self._newest_open_time = self.engine.newest().Timestamp.item()

    def append(self, klines: pd.core.frame.DataFrame):
        _klines = klines.copy()

        _klines.Open_time = pd.to_datetime(_klines.Open_time, unit="s")
        _klines.set_index("Open_time", inplace=True)
        self.engine.append(_klines)

    def _timestamp_delta(self, n: int) -> int:
        seconds_time_frame = time_frame_to_seconds(self.time_frame)
        minimum_n = seconds_time_frame / 60
        return int(seconds_time_frame * (minimum_n + n + 1))

    def _until(self, since: int, n: int) -> int:
        until = since + self._timestamp_delta(n)
        return (
            until if until < self._newest_open_time else self._newest_open_time
        )

    def _since(self, until: int, n: int) -> int:
        since = until - self._timestamp_delta(n)
        return (
            since if since > self._oldest_open_time else self._oldest_open_time
        )

    def get_by_time_range(self, since, until) -> pd.core.frame.DataFrame:
        const = 10 ** 9  # Coversion sec <--> nanosec
        klines_query = """
        SELECT first("Open") AS "Open", max("High") AS "High", min("Low") AS 
        "Low", last("Close") AS "Close", sum("Volume") AS "Volume" FROM 
        "{}"."autogen"."{}" WHERE time >= {} AND 
        time <= {} GROUP BY time({}) FILL(linear)
        """.format(
            self.database,
            self.table,
            str(const * since),
            str(const * until),
            self.time_frame,
        )
        _klines = self.engine.dataframe_query(klines_query)
        klines = _klines.rename(columns={"Timestamp": "Open_time"})
        return klines

    def oldest(self, n=1) -> pd.core.frame.DataFrame:
        _since = self._oldest_open_time
        klines = self.get_by_time_range(
            since=_since, until=self._until(_since, n)
        )
        _len = min(n, len(klines))
        return klines[:_len]

    def newest(self, n=1) -> pd.core.frame.DataFrame:
        klines = pd.DataFrame()
        _until = self._newest_open_time
        _klines = self.get_by_time_range(
            since=self._since(_until, n), until=_until
        )
        _len = min(n, len(_klines))
        klines = klines.append(_klines[-_len:], ignore_index=True)
        return klines

    def oldest_open_time(self) -> int:
        return self.oldest().Open_time.item()

    def newest_open_time(self) -> int:
        return self.newest().Open_time.item()
