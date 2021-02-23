#import json

import pandas as pd
from pony.orm import Database, Json, Optional, Required, Set, commit, sql_debug

from ...config.settings import system_settings
from ...tools.serializers import Deserialize
from ..sql_app.schemas import Modes
from ..time_series_storage import StorageResults

settings = system_settings()
db = Database()
modes = Modes()
db.bind(**settings.relational_database.dict())
sql_debug(settings.sql_debug)


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
    monitor = Optional(lambda: Monitor)  # Foreing key
    portfolio = Optional(Portfolio, cascade_delete=True)
    side = Required(str, default="Zeroed")
    enter_price = Optional(float)
    timestamp = Optional(int)
    exit_reference_price = Optional(float)


class LastCheck(db.Entity, AttributeUpdater):
    Monitor = Optional(lambda: Monitor)  # Foreing key
    by_classifier_at = Optional(int)  # UTC timestamp
    by_stop_loss_at = Optional(int)  # UTC timestamp


class Monitor(db.Entity, AttributeUpdater):
    operation = Optional(lambda: Operation)
    _setup = Optional(Json)
    position = Required(Position, cascade_delete=True)
    last_check = Required(LastCheck, cascade_delete=True)
    trade_log = Set(lambda: TradeLog, cascade_delete=True)
    #is_running = Required(bool, default=True)

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

    def setup(self):
        return Deserialize(name="setup").from_json(self._setup)

    def reset(self):
        self.last_check.update(by_classifier_at=0)
        self.position.update(side="Zeroed")
        self.position.portfolio.update(quote=0.0, base=0.0)
        self.trade_log.clear()
        commit()


class TradeLog(db.Entity):
    monitor = Optional(lambda: Monitor)
    signal = Optional(str)
    timestamp = Optional(int)
    price = Optional(float)
    fee = Optional(float)  # base_asset units
    quote_amount = Optional(float)

class Operation(db.Entity):
    monitors = Set(Monitor, cascade_delete=True)
    mode = Required(str, default=modes.backtesting)
    is_running = Required(bool, default=False)
    _notifier_setup = Required(Json)
    _backtesting_setup = Optional(Json)

    def notifier_setup(self):
        return Deserialize(name="setup").from_json(self._notifier_setup)

    def backtesting_setup(self):
        return Deserialize(name="setup").from_json(self._backtesting_setup)
    
    def reset(self):
        raise NotImplementedError


db.generate_mapping(create_tables=True)
