# pylint: disable=E1120
# pylint: disable=E1123

"""This module deals with timeseries collections saving. Initially
designed for saving klines, it must be able to read write timeseries
collections from/to files and/or databases, abstracting the needed
implementations. For now, it just have influxdb implementation."""

# import collections

import sys
import pandas as pd
from influxdb_client import InfluxDBClient, WriteOptions
from influxdb_client.client.exceptions import InfluxDBError
from .....config.settings import InfluxDbSettings

thismodule = sys.modules[__name__]


class InfluxDb:
    """An interface layer on top of the influxdb python client,
    useful for the rest of the system.

    For influxdb information:
    https://github.com/influxdata/influxdb-client-python
    """

    __slots__ = [
        "settings",
        "bucket",
        "measurement",
    ]

    def __init__(self, bucket: str, measurement: str):
        self.settings = InfluxDbSettings()
        self.bucket = bucket
        self.measurement = measurement

    def append(self, dataframe: pd.core.frame.DataFrame) -> None:
        """Saves a timeseries pandas dataframe on influxdb.

        Args:
            dataframe (pd.core.frame.DataFrame): Timeseries dataframe
        """

        client = InfluxDBClient(**self.settings.credentials)
        write_client = client.write_api(
            write_options=WriteOptions(**self.settings.write_opts)
        )
        write_client.write(
            bucket=self.bucket,
            org=client.org,
            record=dataframe,
            data_frame_measurement_name=self.measurement,
        )
        client.close()

    def _drop_influxdb_columns(
        self,
        dataframe: pd.core.frame.DataFrame,
    ) -> pd.core.frame.DataFrame:
        returned_columns = list(dataframe.columns)
        columns_to_drop = [
            column
            for column in returned_columns
            if column in self.settings.system_columns
        ]
        return dataframe.drop(columns=columns_to_drop)

    def dataframe_query(
        self, query: str, drop_influxdb_columns=True
    ) -> pd.core.frame.DataFrame:
        """Given a sanitized query*, (flux language format, influxdb v2),
        returns the request measurement formated as a pandas dataframe.
        Args:
            query (str): flux query*
            drop_influxdb_columns (bool, optional): If True, drops the
            columns created by the influxdb. Defaults to True.

        Returns:
            pd.core.frame.DataFrame: Pandas dataframe, created from the
            returned influxdb measurement, following the conversion:

            [influx]                 -> [dataframe]
            table.fields.values      -> columns
            table.records.row.values -> row
        """

        client = InfluxDBClient(**self.settings.credentials)
        query_api = client.query_api()

        try:
            dataframe = query_api.query_data_frame(query)
            if not dataframe.empty:
                dataframe = dataframe.rename(columns={"_time": "Timestamp"})
                dataframe.Timestamp = (
                    dataframe.Timestamp.astype("int64") // 10 ** 9
                )
                if drop_influxdb_columns:
                    dataframe = self._drop_influxdb_columns(dataframe)

            client.close()
            return dataframe
        except InfluxDBError as error:
            raise Exception.with_traceback(error) from InfluxDBError
        return None

    def _get_by_range(self, start: int, stop: int) -> pd.core.frame.DataFrame:
        query = """
            from(bucket: "{}")
            |> range(start: {}, stop: {})
            |> filter(fn: (r) => r["_measurement"] == "{}")
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            """.format(
            self.bucket, start, stop, self.measurement
        )
        return self.dataframe_query(query)

    def _get_by_start_n(self, start: int, n: int) -> pd.core.frame.DataFrame:
        query = """
            from(bucket: "{}")
            |> range(start: {}, stop: now())
            |> limit(n:{})
            |> filter(fn: (r) => r["_measurement"] == "{}")
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            """.format(
            self.bucket, start, n, self.measurement
        )
        return self.dataframe_query(query)

    def _get_by_stop_n(self, stop: int, n: int) -> pd.core.frame.DataFrame:
        query = """
            from(bucket: "{}")
            |> range(start: 0, stop: {})
            |> tail(n:{})
            |> filter(fn: (r) => r["_measurement"] == "{}")
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            """.format(
            self.bucket, stop, n, self.measurement
        )
        return self.dataframe_query(query)

    def get(self, **kwargs) -> pd.core.frame.DataFrame:
        """Solves the request, if that contains at least 2 of these
        3 arguments: "start", "stop", "n".

        Returns:
            pd.core.frame.DataFrame: Requested measurement range.
        """
        start: int = kwargs.get("start")
        stop: int = kwargs.get("stop")
        n: int = kwargs.get("n")

        if start and n: # This cover the scenario "start and stop and n"
            dataframe = self._get_by_start_n(start, n)

        elif start and stop and not n:
            dataframe = self._get_by_range(start, stop)

        elif stop and n and not start:
            dataframe = self._get_by_stop_n(stop, n)
        
        else:
            raise ValueError(
                "At least 2 of 3 arguments (start, stop, n) must be passed"
            )
        return dataframe


def instantiate_engine(engine_name: str):
    return getattr(thismodule, engine_name)
