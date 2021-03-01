# pylint: disable=E1120
# pylint: disable=E1123

"""This module deals with timeseries collections saving. Initially
designed for saving klines, it must be able to read write timeseries
collections from/to files and/or databases, abstracting the needed
implementations."""

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

    def _pos_process_dataframe(
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
        self, query: str, pos_processdataframe=True
    ) -> pd.core.frame.DataFrame:
        """Dada uma query tratada*, no formato flux (influxdb v2),
        retorna um dataframe com as informações obtidas.

        Args:
            query (str): flux query*
            pos_processdataframe (bool, optional): Se True, elimina as
            colunas geradas pelo influx. Defaults to True.

        Returns:
            pd.core.frame.DataFrame: Pandas dataframe, criado a partir
            da measurement retornada do influx, seguindo a conversão:

            [influx]                 -> [dataframe]
            table.fields.values      -> columns
            table.records.row.values -> row
        """

        client = InfluxDBClient(**self.settings.credentials)
        query_api = client.query_api()

        try:
            dataframe = query_api.query_data_frame(query)
            if pos_processdataframe:
                dataframe = self._pos_process_dataframe(dataframe)

            dataframe = dataframe.rename(columns={"_time": "Timestamp"})
            dataframe.Timestamp = dataframe.Timestamp.astype("int64") // 10 ** 9
            return dataframe
        except InfluxDBError as error:
            raise Exception.with_traceback(error) from InfluxDBError
        return None


def instantiate_engine(engine_name: str):
    return getattr(thismodule, engine_name)
