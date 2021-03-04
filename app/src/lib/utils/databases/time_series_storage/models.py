import pandas as pd
import pendulum

from ....tools.time_handlers import time_frame_to_seconds
from .engines import InfluxDb


class Storage:
    def __init__(self, repository_name: str, table_name: str):
        self.repository_name = repository_name
        self.table_name = table_name
        self.engine = InfluxDb(bucket=repository_name, measurement=table_name)

    def append(self, dataframe: pd.core.frame.DataFrame):
        self.engine.append(dataframe)

    def get(self, **kwargs):
        return self.engine.get(**kwargs)

    def oldest(self, n=1):
        return self.engine.oldest(n)

    def newest(self, n=1):
        return self.engine.oldest(n)


class Results(Storage):
    def __init__(self, _id: str):
        super().__init__(repository_name="results", table_name=_id)


class KlinesQueryBuilder:
    """Responsible for transforming the klines aggregating
    logic into a query for influxdb"""

    def __init__(self, bucket, start, stop, measurement, time_frame):
        self.time_frame = time_frame
        self.header_query = """
              from(bucket: "{}")
              |> range(start: {}, stop: {})
              |> filter(fn: (r) => r["_measurement"] == "{}")
              """.format(
            bucket, start, stop, measurement
        )
        self.function_filter = {
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
        }

    def _table(self, field: str) -> str:
        table_query = """
          |> filter(fn: (r) => r["_field"] == "{f}")
          |> aggregateWindow(every: {tf}, fn: {func}, createEmpty: true)
          |> pivot(rowKey:["_time","_start", "_stop", "_measurement"], 
          columnKey: ["_field"], valueColumn: "_value")
          |> keep(columns: ["_time","{f}"])
        """.format(
            f=field, tf=self.time_frame, func=self.function_filter[field]
        )
        return self.header_query + table_query

    @staticmethod
    def _joint(tab1: str, tab2: str) -> str:
        return (
            """join(tables: {}tab1: {}, tab2: {}{}, on: ["_time"])""".format(
                "{", tab1, tab2, "}"
            )
        )

    def build(self) -> str:
        """Pipes the joints of two tables by round.

        Returns:
            str: Query formatted in flux language
        """
        query = self._table("Open")
        for field in ["High", "Low", "Close", "Volume"]:
            query = self._joint(query, self._table(field))

        return query


class StorageKlines(Storage):
    def __init__(self, _id: str, time_frame: str):
        super().__init__(repository_name="klines", table_name=_id)
        self.time_frame = time_frame
        self.columns = ["Open_time", "Open", "High", "Low", "Close", "Volume"]

    def append(self, dataframe: pd.core.frame.DataFrame) -> None:
        klines = dataframe.copy()
        self.engine.append(
            dataframe=klines.rename(columns={"Open_time": "Timestamp"})
        )

    def _timestamp_delta(self, n: int) -> int:
        tf_sec = time_frame_to_seconds(self.time_frame)
        _minimal_n = tf_sec / 60
        _raw_n = _minimal_n + n + 2  # +2 for a safety margin.
        return int(tf_sec * _raw_n)

    def _until(self, since: int, n: int) -> int:
        until = since + self._timestamp_delta(n)
        now = pendulum.now("UTC").int_timestamp
        return until if until < now else now

    def _since(self, until: int, n: int) -> int:
        since = until - self._timestamp_delta(n)
        return since if since > 0 else 0

    def get(self, **kwargs) -> pd.core.frame.DataFrame:
        query = KlinesQueryBuilder(
            bucket=self.repository_name,
            start=kwargs["since"],
            stop=kwargs["until"],
            measurement=self.table_name,
            time_frame=self.time_frame,
        ).build()
        klines = self.engine.dataframe_query(query)
        klines = klines.rename(columns={"Timestamp": "Open_time"})

        return klines[self.columns]

    def oldest(self, n: int = 1) -> pd.core.frame.DataFrame:
        _oldest = self.engine.get(start="0", n=1)
        since = _oldest.Timestamp.item()
        klines = self.get(since=str(since), until=str(self._until(since, n)))
        _len = min(n, len(klines))
        return klines[:_len]

    def newest(self, n: int = 1) -> pd.core.frame.DataFrame:
        klines = pd.DataFrame()

        _newest = self.engine.get(stop="now()", n=1)
        until = _newest.Timestamp.item()
        _klines = self.get(since=str(self._since(until, n)), until=str(until))
        _len = min(n, len(_klines))

        klines = klines.append(_klines[-_len:], ignore_index=True)
        return klines
