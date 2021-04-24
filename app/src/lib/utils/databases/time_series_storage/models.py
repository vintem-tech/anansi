import pandas as pd

from ...tools.time_handlers import time_frame_to_seconds
from .engines import InfluxDbV1 as InfluxDb


class StorageKlines:
    __slots__ = [
        "table",
        "database",
        "time_frame",
        "engine",
    ]

    def __init__(self, table: str, time_frame: str):
        self.database = "klines"
        self.table = table
        self.time_frame = time_frame
        self.engine = InfluxDb(self.database, table)

    def append(self, klines: pd.core.frame.DataFrame):
        _klines = klines.copy()

        try:
            _klines.apply_datetime_conversion.from_human_readable_to_timestamp(
                target_columns=["Open_time"]
            )
        except TypeError:  # Datetime values already in timestamp type
            pass

        _klines.Open_time = pd.to_datetime(_klines.Open_time, unit="s")
        _klines.set_index("Open_time", inplace=True)
        self.engine.append(_klines)

    def _timestamp_delta(self, n: int) -> int:
        seconds_time_frame = time_frame_to_seconds(self.time_frame)
        minimum_n = seconds_time_frame / 60
        return int(seconds_time_frame * (minimum_n + n + 1))

    def _until(self, since: int, n: int) -> int:
        until = since + self._timestamp_delta(n)
        newest_open_time = self.engine.newest().Timestamp.item()
        return until if until < newest_open_time else newest_open_time

    def _since(self, until: int, n: int) -> int:
        since = until - self._timestamp_delta(n)
        oldest_open_time = self.engine.oldest().Timestamp.item()

        return since if since > oldest_open_time else oldest_open_time

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
        _since = self.engine.oldest().Timestamp.item()
        klines = self.get_by_time_range(
            since=_since, until=self._until(_since, n)
        )
        _len = min(n, len(klines))
        return klines[:_len]

    def newest(self, n=1) -> pd.core.frame.DataFrame:
        klines = pd.DataFrame()
        _until = self.engine.newest().Timestamp.item()
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


class StorageResults:
    __slots__ = [
        "table",
        "database",
        "engine",
    ]

    def __init__(self, table: str):
        self.database = "results"
        self.table = table
        self.engine = InfluxDb(self.database, table)

    def append(self, dataframe: pd.core.frame.DataFrame):
        try:
            result = dataframe.rename(columns={"Open_time": "Timestamp"})
        except KeyError:  # Datetime column already named "Timestamp"
            result = dataframe

        try:
            result.apply_datetime_conversion.from_human_readable_to_timestamp(
                target_columns=["Timestamp"]
            )
        except TypeError:  # Datetime values already in timestamp type
            pass

        result.Timestamp = pd.to_datetime(result.Timestamp, unit="s")
        result.set_index("Timestamp", inplace=True)
        self.engine.append(result)

    @staticmethod
    def _as_human_readable(
        result: pd.core.frame.DataFrame,
    ) -> pd.core.frame.DataFrame:

        result.apply_datetime_conversion.from_timestamp_to_human_readable(
            target_columns=["Timestamp"]
        )
        return result

    def get(self, **kwargs) -> pd.core.frame.DataFrame:
        return self._as_human_readable(result=self.engine.get(**kwargs))

    def oldest(self, n=1) -> pd.core.frame.DataFrame:
        return self._as_human_readable(result=self.engine.oldest(n))

    def newest(self, n=1) -> pd.core.frame.DataFrame:
        return self._as_human_readable(result=self.engine.oldest(n))


## Influxdb version 2.x Backup

# import pandas as pd
# import pendulum
#
# from ....tools.time_handlers import time_frame_to_seconds
# from .engines import InfluxDb
#
#
# class Storage:
#     def __init__(self, repository_name: str, table_name: str):
#         self.repository_name = repository_name
#         self.table_name = table_name
#         self.engine = InfluxDb(bucket=repository_name, measurement=table_name)
#
#     def append(self, dataframe: pd.core.frame.DataFrame):
#         self.engine.append(dataframe)
#
#     def get(self, **kwargs):
#         return self.engine.get(**kwargs)
#
#     def oldest(self, n=1):
#         return self.engine.oldest(n)
#
#     def newest(self, n=1):
#         return self.engine.oldest(n)
#
#
# class Results(Storage):
#     def __init__(self, _id: str):
#         super().__init__(repository_name="results", table_name=_id)
#
#
# class KlinesQueryBuilder:
#     """Responsible for transforming the klines aggregating
#     logic into a query for influxdb"""
#
#     def __init__(self, bucket, start, stop, measurement, time_frame):
#         self.time_frame = time_frame
#         self.header_query = """
#               from(bucket: "{}")
#               |> range(start: {}, stop: {})
#               |> filter(fn: (r) => r["_measurement"] == "{}")
#               """.format(
#             bucket, start, stop, measurement
#         )
#         self.function_filter = {
#             "Open": "first",
#             "High": "max",
#             "Low": "min",
#             "Close": "last",
#             "Volume": "sum",
#         }
#
#     def _table(self, field: str) -> str:
#         table_query = """
#           |> filter(fn: (r) => r["_field"] == "{f}")
#           |> aggregateWindow(every: {tf}, fn: {func}, createEmpty: true)
#           |> pivot(rowKey:["_time","_start", "_stop", "_measurement"],
#           columnKey: ["_field"], valueColumn: "_value")
#           |> keep(columns: ["_time","{f}"])
#         """.format(
#             f=field, tf=self.time_frame, func=self.function_filter[field]
#         )
#         return self.header_query + table_query
#
#     @staticmethod
#     def _joint(tab1: str, tab2: str) -> str:
#         return (
#             """join(tables: {}tab1: {}, tab2: {}{}, on: ["_time"])""".format(
#                 "{", tab1, tab2, "}"
#             )
#         )
#
#     def build(self) -> str:
#         """Pipes the joints of two tables by round.
#
#         Returns:
#             str: Query formatted in flux language
#         """
#         query = self._table("Open")
#         for field in ["High", "Low", "Close", "Volume"]:
#             query = self._joint(query, self._table(field))
#
#         return query
#
#
# class StorageKlines(Storage):
#     def __init__(self, _id: str, time_frame: str):
#         super().__init__(repository_name="klines", table_name=_id)
#         self.time_frame = time_frame
#         self.columns = ["Open_time", "Open", "High", "Low", "Close", "Volume"]
#
#     def append(self, dataframe: pd.core.frame.DataFrame) -> None:
#         klines = dataframe.copy()
#         self.engine.append(
#             dataframe=klines.rename(columns={"Open_time": "Timestamp"})
#         )
#
#     def _timestamp_delta(self, n: int) -> int:
#         tf_sec = time_frame_to_seconds(self.time_frame)
#         _minimum_n = tf_sec / 60
#         _raw_n = _minimum_n + n + 2  # +2 for a safety margin.
#         return int(tf_sec * _raw_n)
#
#     def _until(self, since: int, n: int) -> int:
#         until = since + self._timestamp_delta(n)
#         now = pendulum.now("UTC").int_timestamp
#         return until if until < now else now
#
#     def _since(self, until: int, n: int) -> int:
#         since = until - self._timestamp_delta(n)
#         return since if since > 0 else 0
#
#     def get(self, **kwargs) -> pd.core.frame.DataFrame:
#         query = KlinesQueryBuilder(
#             bucket=self.repository_name,
#             start=kwargs["since"],
#             stop=kwargs["until"],
#             measurement=self.table_name,
#             time_frame=self.time_frame,
#         ).build()
#         klines = self.engine.dataframe_query(query)
#         klines = klines.rename(columns={"Timestamp": "Open_time"})
#
#         return klines[self.columns]
#
#     def oldest(self, n: int = 1) -> pd.core.frame.DataFrame:
#         _oldest = self.engine.get(start="0", n=1)
#         print(_oldest)
#         since = _oldest.Timestamp.item()
#         klines = self.get(since=str(since), until=str(self._until(since, n)))
#         _len = min(n, len(klines))
#         return klines[:_len]
#
#     def newest(self, n: int = 1) -> pd.core.frame.DataFrame:
#         klines = pd.DataFrame()
#
#         _newest = self.engine.get(stop="now()", n=1)
#         until = _newest.Timestamp.item()
#         _klines = self.get(since=str(self._since(until, n)), until=str(until))
#         _len = min(n, len(_klines))
#
#         klines = klines.append(_klines[-_len:], ignore_index=True)
#         return klines
#
