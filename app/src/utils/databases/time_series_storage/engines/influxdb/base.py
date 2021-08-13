import pandas as pd


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
