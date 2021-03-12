import collections

import sys
import pandas as pd
from environs import Env
from influxdb import DataFrameClient  # Influxdb v1.8

thismodule = sys.modules[__name__]

env = Env()

influxdb_params = dict(
    host=env.str("INFLUXDB_HOST", default="localhost"),
    port=env.int("INFLUXDB_PORT", default=8086),
    username=env.str("INFLUXDB_USER", default="Anansi"),
    password=env.str("INFLUXDB_USER_PASSWORD", default="anansi2020"),
    gzip=env.bool("INFLUXDB_GZIP", default=True),
)


class InfluxDb:

    """For influxdb information:
    https://influxdb-python.readthedocs.io/en/latest/api-documentation.html#dataframeclient
    """

    __slots__ = [
        "database",
        "measurement",
    ]

    def __init__(self, database: str, measurement: str):
        self.database = database
        self.measurement = measurement

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
        client = DataFrameClient(**influxdb_params)
        client.create_database(self.database)

        client.write_points(
            dataframe=dataframe,
            measurement=self.measurement,
            tags=None,
            tag_columns=None,
            field_columns=list(dataframe.columns),
            time_precision=None,
            database=self.database,
            # retention_policy=None,
            batch_size=None,
            protocol="line",
            numeric_precision=None,
        )
        client.close()

    def proceed(self, query_to_proceed) -> collections.defaultdict:
        client = DataFrameClient(**influxdb_params)
        query_result = client.query(query_to_proceed)
        client.close()
        return query_result
