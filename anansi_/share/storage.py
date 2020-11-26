import pandas as pd

class StorageKlines:
    def __init__(self, table_name:str):
        self.table_name = table_name
    
    def append(self, dataframe:pd.core.frame.DataFrame):
        self._save_in_slices(dataframe)

    def _save_in_slices(self, dataframe_in, step=500):
        _end = len(dataframe_in)

        for i in range(0, _end, step):
            _from, _until = i, i + step

            if _until > _end:
                _until = _end
            self._append_dataframe(dataframe_in[_from:_until])

    def _append_dataframe(self, dataframe_to_append):

        try:
            with sqlite3.connect(self._db_name) as conn:
                dataframe_to_append.to_sql(
                    name=self._table_name,
                    con=conn,
                    if_exists="append",
                    index=False,
                    index_label=self._primary_key,
                    method="multi")

        except (Exception, sqlite3.OperationalError) as e:
            print(e)

        finally:
            conn.close()

    def _proceed_search(self, query="") -> list:
        _query = "SELECT * FROM {} {};".format(self._table_name, query)
        search_result = []
        try:
            with sqlite3.connect(self._db_name) as conn:
                c = conn.cursor()
                c.execute(_query)
                search_result = c.fetchall()

        except (Exception, sqlite3.OperationalError) as e:
            print(e)

        finally:
            c.close()
            conn.close()
