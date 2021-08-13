# pylint: disable=unexpected-keyword-arg
# pylint: disable=no-value-for-parameter

import pandas as pd

from influxdb import DataFrameClient

from ......config.databases import InfluxDbSettings
from .base import Engine


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
        _dataframe.Timestamp = _dataframe.Timestamp.view("int64") // 10 ** 9

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
