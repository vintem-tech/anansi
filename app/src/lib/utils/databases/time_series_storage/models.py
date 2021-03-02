# import numpy as np
import pandas as pd

from .engines import InfluxDb
from ....tools.time_handlers import time_frame_to_seconds


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
        raise NotImplementedError

    def newest(self, n=1):
        raise NotImplementedError


class Results(Storage):
    def __init__(self, _id: str):
        super().__init__(repository_name="results", table_name=_id)

    def oldest(self, n=1):
        return self.engine.get(start=0, n=n)

    def newest(self, n=1):
        return self.engine.get(stop="now()", n=n)


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
          |> filter(fn: (r) => r["_field"] == "{}")
          |> aggregateWindow(every: {}, fn: {}, createEmpty: true)
          |> pivot(rowKey:["_time","_start", "_stop", "_measurement"], 
          columnKey: ["_field"], valueColumn: "_value")
          |> keep(columns: ["_time","{}"])
        """.format(
            field, self.time_frame, self.function_filter[field], field
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


class Klines(Storage):
    def __init__(self, _id: str, time_frame: str):
        super().__init__(repository_name="klines", table_name=_id)
        self.time_frame = time_frame

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

        return klines

    def _minimal_n(self):
        return time_frame_to_seconds(self.time_frame) / 60 + 2

    def _fake_until(self, fake_since, n):
        return fake_since + (n + self._minimal_n()) * 60

    def _fake_since(self, fake_until, n):
        _since = fake_until - (n + self._minimal_n()) * 60
        return _since if _since > 0 else 0

    def oldest(self, n=1):
        _oldest = self.engine.get(start=0, n=1)
        fake_since = _oldest.Timestamp.item()
        fake_until = self._fake_until(fake_since, n)
        klines = self.get(since=fake_since, until=fake_until)
        return klines[:n]

    def newest(self, n=1):
        _newest = self.engine.get(stop="now()", n=1)
        fake_until = _newest.Timestamp.item()
        fake_since = self._fake_since(fake_until, n)
        klines = self.get(since=fake_since, until=fake_until)
        return klines[-n:]
