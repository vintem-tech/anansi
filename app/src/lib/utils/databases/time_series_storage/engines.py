# pylint: disable=E1120
# pylint: disable=E1123

"""This module deals with timeseries collections saving. Initially
designed for saving klines, it must be able to read write timeseries
collections from/to files and/or databases, abstracting the needed
implementations."""

import collections

import sys
import pandas as pd
from influxdb import DataFrameClient  # Influxdb v1.8
from .....config.settings import TimeSerieDatabaseEngines

engines = TimeSerieDatabaseEngines()

thismodule = sys.modules[__name__]


class InfluxDb:
    """For influxdb information:
    https://influxdb-python.readthedocs.io/en/latest/api-documentation.html#dataframeclient
    """

    __slots__ = [
        "client",
        "database",
        "measurement",
    ]

    def __init__(self, database: str, measurement: str):
        self.client = DataFrameClient(**engines.influx_db)
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
        self.client.create_database(self.database)

        self.client.write_points(
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
        self.client.close()

    def proceed(self, query_to_proceed) -> collections.defaultdict:
        query_result = self.client.query(query_to_proceed)
        self.client.close()
        return query_result


def instantiate_engine(engine_name: str):
    return getattr(thismodule, engine_name)


# (influxdb:v2.0.2)

# ## Image for docker-compose:

#   influxdb:
#     image: quay.io/influxdb/influxdb:v2.0.2


# ## References:

# https://github.com/influxdata/influxdb-client-python
# https://docs.influxdata.com/influxdb/v2.0/tools/client-libraries/python/

# ## Basic script to append dataframes to buckets

# import influxdb_client
# from influxdb_client.client.write_api import SYNCHRONOUS
# import pandas as pd

# bucket = "<bucket>"
# org = "<organization>"
# token = "<token>"
# url="http://localhost:8086"

# client = influxdb_client.InfluxDBClient(
#   url=url,
#   token=token,
#   org=org,
#   enable_gzip=True
# )

# write_api = client.write_api(write_options=SYNCHRONOUS)

# work_klines = my_klines.copy()

# work_klines.KlinesDateTime.from_human_readable_to_timestamp()

# work_klines.Open_time = pd.to_datetime(work_klines.Open_time, unit="s")
# work_klines.set_index("<date_time-timestamp>", inplace=True)

# write_api .write(bucket=bucket,
#                  org=org,
#                  record=work_klines,
#                  data_frame_measurement_name='<measurement_name>')
