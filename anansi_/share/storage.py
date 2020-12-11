"""Este módulo tem por objetivo lidar com o salvamento de coleções. Inicialmente
pensado para cobrir a tarefa de salvar klines, deve ser capaz de ler/escrever
coleções de/em arquivos e/ou banco de dados, servindo como uma camada de
implementação e provendo uma interface para este fim"""

import pandas as pd
import numpy as np
from environs import Env
import collections

env = Env()

influxdb_params = dict(
    host=env.str("INFLUXDB_HOST", default="localhost"),
    port=env.int("INFLUXDB_PORT", 8086),
    username=env.str("INFLUXDB_USER", default="Anansi"),
    password=env.str("INFLUXDB_USER_PASSWORD", default="anansi2020"),
    gzip=env.bool("INFLUXDB_GZIP", default=True),
)


# Influxdb v1.8

from influxdb import DataFrameClient


class InfluxDb:

    """For influxdb information:
    https://influxdb-python.readthedocs.io/en/latest/api-documentation.html#dataframeclient

    For retention policy:

    client.create_retention_policy(name="long_duration", replication=1, duration='INF')
    client.alter_retention_policy(name="short_duration", replication=1, duration='10d')"""

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


class StorageKlines:
    __slots__ = [
        "table",
        "database",
        "agent",
    ]

    def __init__(self, table: str, database: str):
        self.table = table
        self.database = database
        self.agent = InfluxDb(database=database, measurement=table)

    def _seconds_timestamp_of_oldest_record(self) -> int:
        oldest_query = """
            SELECT * FROM "{}"."autogen"."{}" GROUP BY * ORDER BY ASC LIMIT 1
            """.format(
            self.database,
            "Binance_btcusdt_1m",
            # self.table,
        )
        oldest = (self.agent.proceed(oldest_query))["Binance_btcusdt_1m"]
        return int(pd.Timestamp(oldest.index[0]).timestamp())

    def _seconds_timestamp_of_newest_record(self) -> int:
        newest_query = """
            SELECT * FROM "{}"."autogen"."{}" GROUP BY * ORDER BY DESC LIMIT 1
            """.format(
            self.database,
            "Binance_btcusdt_1m",
            # self.table,
        )
        newest = (self.agent.proceed(newest_query))["Binance_btcusdt_1m"]
        return int(pd.Timestamp(newest.index[0]).timestamp())

    def append(self, klines: pd.core.frame.DataFrame):
        work_klines = klines.copy()

        work_klines.Open_time = pd.to_datetime(work_klines.Open_time, unit="s")
        work_klines.set_index("Open_time", inplace=True)
        self.agent.append(work_klines)

    def get_klines(
        self, start_time: int, end_time: int, time_frame: str
    ) -> pd.core.frame.DataFrame:
        const = 10 ** 9  # Coversion sec <--> nanosec

        klines_query = """
        SELECT first("Open") AS "Open", max("High") AS "High", min("Low") AS 
        "Low", last("Close") AS "Close", sum("Volume") AS "Volume" FROM 
        "{}"."autogen"."{}" WHERE time >= {} AND 
        time <= {} GROUP BY time({}) FILL(linear)
        """.format(
            self.database,
            "Binance_btcusdt_1m",
            # self.table,
            str(const * start_time),
            str(const * end_time),
            time_frame,
        )
        _klines = self.agent.proceed(klines_query)
        # klines = _klines[self.table]
        klines = _klines["Binance_btcusdt_1m"]
        klines.reset_index(inplace=True)
        klines = klines.rename(columns={"index": "Open_time"})
        klines.Open_time = klines.Open_time.values.astype(np.int64) // const
        return klines


"""(influxdb:v2.0.2)

## Image for docker-compose:

  influxdb:
    image: quay.io/influxdb/influxdb:v2.0.2


## References:

https://github.com/influxdata/influxdb-client-python
https://docs.influxdata.com/influxdb/v2.0/tools/client-libraries/python/


## Basic script to append dataframes to buckets

import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd

bucket = "<bucket>"
org = "<organization>"
token = "<token>"
url="http://localhost:8086"

client = influxdb_client.InfluxDBClient(
  url=url,
  token=token,
  org=org,
  enable_gzip=True
)

write_api = client.write_api(write_options=SYNCHRONOUS)

work_klines = my_klines.copy()

work_klines.KlinesDateTime.from_human_readable_to_timestamp()

work_klines.Open_time = pd.to_datetime(work_klines.Open_time, unit="s")
work_klines.set_index("<date_time-timestamp>", inplace=True)

write_api .write(bucket=bucket,
                 org=org,
                 record=work_klines,
                 data_frame_measurement_name='<measurement_name>')
"""
