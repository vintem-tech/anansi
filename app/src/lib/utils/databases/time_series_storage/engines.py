# pylint: disable=unexpected-keyword-arg
# pylint: disable=no-value-for-parameter

"""An interface layer over influxdb timeseries database.
Documentation: https://www.influxdata.com/"""

import sys

import pandas as pd
from influxdb import DataFrameClient  # For influxdb v1.x

# For influxdb v2.x:
from influxdb_client import InfluxDBClient
from influxdb_client.client.exceptions import InfluxDBError
from influxdb_client.client.write_api import ASYNCHRONOUS

from .....config.settings import InfluxDbSettings

thismodule = sys.modules[__name__]


class Engine:
    __slots__ = [
        "database",
        "table",
    ]

    def __init__(self, database: str, table: str):
        self.database = database
        self.table = table

    def append(self, dataframe: pd.core.frame.DataFrame) -> None:
        raise NotImplementedError

    def dataframe_query(self, query: str) -> pd.core.frame.DataFrame:
        raise NotImplementedError

    def get(self, **kwargs) -> pd.core.frame.DataFrame:
        """Solves the request, if that contains at least 2 of these
        3 arguments: "start", "stop", "n".

        Returns:
            pd.core.frame.DataFrame: Requested measurement range.
        """

        raise NotImplementedError

    def oldest(self, n=1):
        raise NotImplementedError

    def newest(self, n=1):
        raise NotImplementedError


class InfluxDbV1(Engine):
    """Documentation:
    https://influxdb-python.readthedocs.io/en/latest/api-documentation.html
    """

    __slots__ = [
        "settings",
    ]

    def __init__(self, database: str, table: str):
        super().__init__(database, table)
        self.settings = InfluxDbSettings().V1

    def append(self, dataframe: pd.core.frame.DataFrame) -> None:
        """Saves a timeseries pandas dataframe on influxdb.

        Args:
            dataframe (pd.core.frame.DataFrame): Timeseries dataframe

        For retention policy, follow below example, and declare the
        'retention_policy=name' at 'client.write_points':

        client.create_retention_policy(name="long_duration",
        replication=1, duration='INF') or

        client.alter_retention_policy(name="short_duration",
        replication=1, duration='10d')
        """
        client = DataFrameClient(**self.settings.credentials)
        client.create_database(self.database)

        client.write_points(
            dataframe=dataframe,
            measurement=self.table,
            tags=None,
            tag_columns=None,
            field_columns=list(dataframe.columns),
            time_precision=None,
            database=self.database,
            batch_size=None,
            protocol="line",
            numeric_precision=None,
        )
        client.close()

    def dataframe_query(self, query) -> pd.core.frame.DataFrame:
        """Given a sanitized query (InfluxQL language), returns the
        requested measurement formated as a pandas dataframe."""

        client = DataFrameClient(**self.settings.credentials)
        query_result = client.query(query)
        client.close()

        _dataframe = list(query_result.values())[0]
        _dataframe.reset_index(inplace=True)
        _dataframe = _dataframe.rename(columns={"index": "Timestamp"})
        _dataframe.Timestamp = _dataframe.Timestamp.astype("int64") // 10 ** 9

        return _dataframe

    def get(self, **kwargs) -> pd.core.frame.DataFrame:
        raise NotImplementedError

    def oldest(self, n=1) -> pd.core.frame.DataFrame:
        query = """SELECT * FROM "{}"."autogen"."{}" ORDER BY ASC LIMIT {}
        """.format(
            self.database, self.table, n
        )
        return self.dataframe_query(query)

    def newest(self, n=1):
        query = """SELECT * FROM "{}"."autogen"."{}" ORDER BY DESC LIMIT {}
        """.format(
            self.database, self.table, n
        )
        return self.dataframe_query(query)


class InfluxDbV2(Engine):
    """An interface layer on top of the influxdb v2.x python client,
    useful for the rest of the system.

    Documentation:
    https://github.com/influxdata/influxdb-client-python
    """

    __slots__ = [
        "settings",
        "drop_influxdb_columns",
    ]

    def __init__(self, database: str, table: str):
        super().__init__(database, table)
        self.settings = InfluxDbSettings().V2
        self.drop_influxdb_columns = True

    def append(self, dataframe: pd.core.frame.DataFrame) -> None:
        """Saves a timeseries pandas dataframe on influxdb.

        Args:
            dataframe (pd.core.frame.DataFrame): Timeseries dataframe
        """

        dataframe.Timestamp = pd.to_datetime(dataframe.Timestamp, unit="s")
        dataframe.set_index("Timestamp", inplace=True)

        client = InfluxDBClient(**self.settings.credentials)
        write_client = client.write_api(
            # write_options=WriteOptions(**self.settings.write_opts),
            write_options=ASYNCHRONOUS,
        )
        write_client.write(
            bucket=self.database,
            org=client.org,
            record=dataframe,
            data_frame_measurement_name=self.table,
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

    def dataframe_query(self, query: str) -> pd.core.frame.DataFrame:
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
                if self.drop_influxdb_columns:
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
            self.database, start, stop, self.table
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
            self.database, start, n, self.table
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
            self.database, stop, n, self.table
        )
        return self.dataframe_query(query)

    def get(self, **kwargs) -> pd.core.frame.DataFrame:
        """Solves the request, if that contains at least 2 of these
        3 arguments: "start", "stop", "n".

        Returns:
            pd.core.frame.DataFrame: Requested measurement range.
        """

        start = kwargs.get("start")
        stop = kwargs.get("stop")
        n = kwargs.get("n")

        if start and n:  # This cover the scenario "start and stop and n"
            dataframe = self._get_by_start_n(start, n)

        elif start and stop and not n:
            dataframe = self._get_by_range(start, stop)

        elif stop and n and not start:
            dataframe = self._get_by_stop_n(stop, n)

        else:
            dataframe = pd.DataFrame()
            raise ValueError(
                "At least 2 of 3 arguments (start, stop, n) must be passed"
            )
        return dataframe

    def oldest(self, n=1):
        _dataframe = self.get(start="0", n=n)
        _len = min(n, len(_dataframe))
        return _dataframe[:_len]

    def newest(self, n=1):
        _dataframe = self.get(stop="now()", n=n)
        _len = min(n, len(_dataframe))
        return _dataframe[-_len:]
