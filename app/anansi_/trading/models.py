import pandas as pd
import json
from environs import Env
from pony.orm import Database, Json, Optional, Required, Set, commit, sql_debug

from ..storage.storage import StorageResults
from ..sql_app.schemas import OperationalSetup

env = Env()
db = Database()

db_host = env.str("DB_HOST", default="localhost")
postgres_db = env.str("POSTGRES_DB", default="ANANSI")
postgres_user = env.str("POSTGRES_USER", default="anansi")
postgres_password = env.str("POSTGRES_PASSWORD", default="anansi")

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


class Portfolio(db.Entity, AttributeUpdater):
    position = Optional(lambda: Position)  # Foreing key
    quote = Optional(float)
    base = Optional(float)


class Position(db.Entity, AttributeUpdater):
    operation = Optional(lambda: Operation)  # Foreing key
    portfolio = Optional(Portfolio, cascade_delete=True)
    side = Required(str, default="Zeroed")
    enter_price = Optional(float)
    timestamp = Optional(int)
    exit_reference_price = Optional(float)


class LastCheck(db.Entity, AttributeUpdater):
    Operation = Optional(lambda: Operation)  # Foreing key
    by_classifier_at = Optional(int)  # UTC timestamp
    by_stop_loss_at = Optional(int)  # UTC timestamp


class Operation(db.Entity, AttributeUpdater):
    setup = Optional(Json)
    position = Required(Position, cascade_delete=True)
    last_check = Required(LastCheck, cascade_delete=True)
    trade_log = Set(lambda: TradeLog, cascade_delete=True)
    is_running = Required(bool, default="is_running")

    def save_result(
        self, database: str, result: pd.core.frame.DataFrame
    ) -> None:
        storage = StorageResults(table=str(self.id), database=database)
        storage.append(result)

    def get_last_result(self) -> pd.core.frame.DataFrame:
        raise NotImplementedError

    def report_trade(self, payload):
        self.trade_log.create(**payload)
        commit()

    def reset(self):
        self.last_check.update(by_classifier_at=0)
        self.position.update(side="Zeroed")
        self.position.portfolio.update(quote=0.0, base=1000.00)
        self.trade_log.clear()
        commit()

    def operational_setup(self) -> OperationalSetup:
        return OperationalSetup(**json.loads(self.setup))


class TradeLog(db.Entity):
    operation = Optional(lambda: Operation)
    signal = Optional(str)
    timestamp = Optional(int)
    price = Optional(float)
    fee = Optional(float)  # base_asset units
    quote_amount = Optional(float)


db.generate_mapping(create_tables=True)
