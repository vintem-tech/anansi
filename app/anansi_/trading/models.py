import pandas as pd
from environs import Env
from pony.orm import Database, Json, Optional, Required, Set, commit, sql_debug

from ..storage.storage import StorageResults

env = Env()
db = Database()

# db_host = env.str("DB_HOST")
# postgres_db = env.str("POSTGRES_DB")
# postgres_user = env.str("POSTGRES_USER")
# postgres_password = env.str("POSTGRES_PASSWORD")

db_host = "localhost"
postgres_db = "ANANSI"
postgres_user = "anansi"
postgres_password = "anansi"

_ORM_bind_to = dict(
    provider="postgres",
    user=postgres_user,
    password=postgres_password,
    host=db_host,
    database=postgres_db,
)

db.bind(**_ORM_bind_to)
sql_debug(env.bool("SQL_DEBUG", default=False))


class AttributeUpdater(object):
    def update(self, **kwargs):
        for item in kwargs.items():
            setattr(self, item[0], item[1])
            commit()


class Position(db.Entity, AttributeUpdater):
    operation = Optional(lambda: Operation)  # Foreing key
    side = Required(str, default="Zeroed")
    enter_price = Optional(float)
    exit_reference_price = Optional(float)


class LastCheck(db.Entity, AttributeUpdater):
    Operation = Optional(lambda: Operation)  # Foreing key
    by_classifier_at = Optional(int)  # UTC timestamp
    by_stop_loss_at = Optional(int)  # UTC timestamp


class Operation(db.Entity, AttributeUpdater):
    setup = Optional(Json)
    position = Required(Position, cascade_delete=True)
    is_running = Required(bool, default="is_running")
    last_check = Required(LastCheck)
    trade_log = Set(lambda: TradeLog)
    current_result = pd.DataFrame()

    def update_current_result(self, result: pd.core.frame.DataFrame) -> None:
        self.current_result[list(result.columns)] = result

    def save_current_result(self):
        storage = StorageResults(table=self.id, database="results")
        storage.append(self.current_result)

    def get_last_result(self) -> pd.core.frame.DataFrame:
        raise NotImplementedError

    def report_trade(self, payload):
        self.trade_log.create(**payload)
        commit()


class TradeLog(db.Entity, AttributeUpdater):
    operation = Optional(lambda: Operation)
    timestamp = Optional(int)
    signal = Optional(str)
    price = Optional(float)
    fee = Optional(float)  # base_asset units
    quote_amount = Optional(float)


db.generate_mapping(create_tables=True)
