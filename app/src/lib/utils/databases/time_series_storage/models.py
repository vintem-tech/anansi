import numpy as np

from .engines import instantiate_engine, pd

engine = instantiate_engine("InfluxDb")


class StorageKlines:
    __slots__ = [
        "engine",
        "table",
        "database",
    ]

    def __init__(self, database: str, table: str):
        self.engine = engine(database, table)
        self.database = database
        self.table = table

    def seconds_timestamp_of_oldest_record(self, time_frame: str) -> int:
        oldest_query = """
            SELECT first("Open") AS "Open" FROM "{}"."autogen"."{}" GROUP BY
            time({}) FILL(linear) ORDER BY ASC LIMIT 1
            """.format(
            self.database, self.table, time_frame
        )
        oldest = (self.engine.proceed(oldest_query))[self.table]
        return int(pd.Timestamp(oldest.index[0]).timestamp())

    def seconds_timestamp_of_newest_record(self, time_frame: str) -> int:
        newest_query = """
            SELECT first("Open") AS "Open" FROM "{}"."autogen"."{}" GROUP BY
            time({}) FILL(linear) ORDER BY DESC LIMIT 1
            """.format(
            self.database, self.table, time_frame
        )
        newest = (self.engine.proceed(newest_query))[self.table]
        return int(pd.Timestamp(newest.index[0]).timestamp())

    def append(self, klines: pd.core.frame.DataFrame):
        work_klines = klines.copy()

        work_klines.Open_time = pd.to_datetime(work_klines.Open_time, unit="s")
        work_klines.set_index("Open_time", inplace=True)
        self.engine.append(work_klines)

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
        return self.engine.proceed(klines_query)

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


class StorageResults:
    __slots__ = [
        "engine",
        "table",
        "database",
    ]

    def __init__(self, table: str, database: str):
        self.engine = engine(database=database, measurement=table)
        self.table = table
        self.database = database

    def oldest_record(self) -> int:
        oldest_query = """
            SELECT * FROM "{}"."autogen"."{}" GROUP BY * ORDER BY ASC LIMIT 1
            """.format(
            self.database,
            self.table,
        )
        return (self.engine.proceed(oldest_query))[self.table]

    def newest_record(self) -> int:
        newest_query = """
            SELECT * FROM "{}"."autogen"."{}" GROUP BY * ORDER BY DESC LIMIT 1
            """.format(
            self.database,
            self.table,
        )
        return (self.engine.proceed(newest_query))[self.table]

    def append(self, result: pd.core.frame.DataFrame):
        work_result = result.copy()

        # work_result.KlinesDateTime.from_human_readable_to_timestamp()
        # work_result.Open_time = pd.to_datetime(work_result.Open_time, unit="s")
        # work_result.set_index("Open_time", inplace=True)

        work_result.timestamp = pd.to_datetime(work_result.timestamp, unit="s")
        work_result.set_index("timestamp", inplace=True)
        self.engine.append(work_result)

    def get_results(
        self, start_time: int, end_time: int
    ) -> pd.core.frame.DataFrame:
        const = 10 ** 9  # Coversion sec <-> nanosec

        results_query = """SELECT * FROM "{}"."autogen"."{}" WHERE time >= {}
        AND time <= {} FILL(linear)""".format(
            self.database,
            self.table,
            str(const * start_time),
            str(const * end_time),
        )
        _results = self.engine.proceed(results_query)
        results = _results[self.table]

        results.reset_index(inplace=True)
        results = results.rename(columns={"index": "timestamp"})
        results.timestamp = results.timestamp.values.astype(np.int64) // const
        return results
