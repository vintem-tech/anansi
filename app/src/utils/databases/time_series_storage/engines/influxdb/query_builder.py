# pylint: disable=too-few-public-methods

"""Generates queries"""

class KlinesInfluxDbV2:
    """Responsible for transforming the klines aggregating
    logic into a consistent flux language query."""

    def __init__(self, bucket, measurement):
        self.bucket = bucket
        self.measurement = measurement

        self.time_frame = str()
        self.query_header = str()

        self.function_filter = {
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
        }

    def _create_query_header(self, start, stop):
        self.query_header = """
              from(bucket: "{}")
              |> range(start: {}, stop: {})
              |> filter(fn: (r) => r["_measurement"] == "{}")
              """.format(
            self.bucket, start, stop, self.measurement
        )

    def _set_time_frame(self, time_frame):
        self.time_frame = time_frame

    def _table(self, field: str) -> str:
        table_query = """
          |> filter(fn: (r) => r["_field"] == "{f}")
          |> aggregateWindow(every: {tf}, fn: {func}, createEmpty: true)
          |> pivot(rowKey:["_time","_start", "_stop", "_measurement"], 
          columnKey: ["_field"], valueColumn: "_value")
          |> keep(columns: ["_time","{f}"])
        """.format(
            f=field, tf=self.time_frame, func=self.function_filter[field]
        )
        return self.query_header + table_query

    @staticmethod
    def _joint(tab1: str, tab2: str) -> str:
        return (
            """join(tables: {}tab1: {}, tab2: {}{}, on: ["_time"])""".format(
                "{", tab1, tab2, "}"
            )
        )

    def build(self, start, stop, time_frame) -> str:
        """Pipes the joints of two tables by round.

        Returns:
            str: Query formatted in flux language
        """

        self._set_time_frame(time_frame)
        self._create_query_header(start, stop)

        query = self._table("Open")
        for field in ["High", "Low", "Close", "Volume"]:
            query = self._joint(query, self._table(field))
        return query
