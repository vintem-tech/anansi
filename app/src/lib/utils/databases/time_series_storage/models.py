import pandas as pd
from .engines import InfluxDbV1 as InfluxDb





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

    def seconds_timestamp_of_oldest_record(self, time_frame: str) -> int:
        oldest_query = """
            SELECT first("Open") AS "Open" FROM "{}"."autogen"."{}" GROUP BY
            time({}) FILL(linear) ORDER BY ASC LIMIT 1
            """.format(
            self.database,
            self.table,
            time_frame
        )
        oldest = (self.agent.proceed(oldest_query))[self.table]
        return int(pd.Timestamp(oldest.index[0]).timestamp())

    def seconds_timestamp_of_newest_record(self, time_frame: str) -> int:
        newest_query = """
            SELECT first("Open") AS "Open" FROM "{}"."autogen"."{}" GROUP BY
            time({}) FILL(linear) ORDER BY DESC LIMIT 1
            """.format(
            self.database,
            self.table,
            time_frame
        )
        newest = (self.agent.proceed(newest_query))[self.table]
        return int(pd.Timestamp(newest.index[0]).timestamp())

    def append(self, klines: pd.core.frame.DataFrame):
        work_klines = klines.copy()

        work_klines.Open_time = pd.to_datetime(work_klines.Open_time, unit="s")
        work_klines.set_index("Open_time", inplace=True)
        self.agent.append(work_klines)

    def get_raw_klines(self, start_time: int, end_time: int, time_frame: str):
        const = 10 ** 9  # Coversion sec <--> nanosec
        klines_query = """
        SELECT first("Open") AS "Open", max("High") AS "High", min("Low") AS 
        "Low", last("Close") AS "Close", sum("Volume") AS "Volume" FROM 
        "{}"."autogen"."{}" WHERE time >= {} AND 
        time <= {} GROUP BY time({}) FILL(linear)
        """.format(
            self.database,
            self.table,
            str(const * start_time),
            str(const * end_time),
            time_frame,
        )
        return self.agent.proceed(klines_query)

    def get_klines(
        self, start_time: int, end_time: int, time_frame: str
    ) -> pd.core.frame.DataFrame:
        const = 10 ** 9  # Coversion sec <--> nanosec

        _klines = self.get_raw_klines(start_time, end_time, time_frame)
        klines = _klines[self.table]

        klines.reset_index(inplace=True)
        klines = klines.rename(columns={"index": "Open_time"})
        klines.Open_time = klines.Open_time.values.astype(np.int64) // const
        return klines

