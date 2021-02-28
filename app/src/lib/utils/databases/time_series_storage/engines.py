# pylint: disable=E1120
# pylint: disable=E1123

"""This module deals with timeseries collections saving. Initially
designed for saving klines, it must be able to read write timeseries
collections from/to files and/or databases, abstracting the needed
implementations."""

#import collections

import sys
import pandas as pd

# from influxdb import DataFrameClient  # Influxdb v1.8
from influxdb_client import InfluxDBClient, WriteOptions
from .....config.settings import InfluxDbSettings

influx_settings = InfluxDbSettings()

thismodule = sys.modules[__name__]


class InfluxDb:
    """For influxdb information:
    https://github.com/influxdata/influxdb-client-python
    """

    __slots__ = [
        "bucket",
        "measurement",
    ]

    def __init__(self, bucket: str, measurement: str):
        self.bucket = bucket
        self.measurement = measurement

    def append(self, dataframe: pd.core.frame.DataFrame) -> None:
        """Saves a timeseries pandas dataframe on influxdb.

        Args:
            dataframe (pd.core.frame.DataFrame): Timeseries dataframe
        """

        client = InfluxDBClient(**influx_settings.credentials)
        write_client = client.write_api(
            write_options=WriteOptions(**influx_settings.write_opts)
        )
        write_client.write(
            bucket=self.bucket,
            org=client.org,
            record=dataframe,
            data_frame_measurement_name=self.measurement,
        )
        client.close()

    #    def proceed(self, query_to_proceed) -> collections.defaultdict:
    #        query_result = self.client.query(query_to_proceed)
    #        self.client.close()
    #        return query_result


def instantiate_engine(engine_name: str):
    return getattr(thismodule, engine_name)