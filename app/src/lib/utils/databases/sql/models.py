import json

import pandas as pd
from pony.orm import Database, Json, Optional, Required, Set, commit, sql_debug

from .....config.settings import system_settings
from ....tools.serializers import Deserialize
from ..sql.schemas import OperationalModes
from ..time_series_storage.models import StorageResults

settings = system_settings()
db = Database()
modes = OperationalModes()
db.bind(**settings.relational_database.dict())
sql_debug(settings.sql_debug)


class AttributeUpdater(object):
    def update(self, **kwargs):
        for attribute, value in kwargs.items():
            setattr(self, attribute, value)
            commit()


# class User(db.Entity, AttributeUpdater):
#    raise NotImplementedError


# class Settings(db.Entity, AttributeUpdater):
#    raise NotImplementedError


#class Portfolio(db.Entity, AttributeUpdater):
#    position = Optional(lambda: Position)  # Foreing key
#    quote = Optional(float)
#    base = Optional(float)


class Position(db.Entity, AttributeUpdater):
    monitor = Optional(lambda: Monitor)  # Foreing key
#    portfolio = Optional(Portfolio, cascade_delete=True)
    side = Required(str, default="Zeroed")
    size = Required(float, default=0.0) # by quote
    enter_price = Optional(float)
    timestamp = Optional(int)
    exit_reference_price = Optional(float)


class LastCheck(db.Entity, AttributeUpdater):
    monitor = Optional(lambda: Monitor)  # Foreing key
    by_classifier_at = Optional(int)  # UTC timestamp
    by_stop_loss_at = Optional(int)  # UTC timestamp


class Monitor(db.Entity, AttributeUpdater):
    operation = Optional(lambda: Operation)
    is_active = Required(bool, default=True)
    is_master = Required(bool, default=False)
    _market = Required(Json)
    position = Required(Position, cascade_delete=True)
    last_check = Required(LastCheck, cascade_delete=True)
    trade_logs = Set(lambda: TradeLog, cascade_delete=True)

    def market(self):
        return Deserialize(name="market").from_json(self._market)

    def save_result(self, result_type: str, result: pd.core.frame.DataFrame):
        op_name = self.operation.name
        exchange = self.market().exchange
        symbol = self.market().ticker_symbol
        table = "{}_{}_{}_{}".format(op_name, exchange, symbol, result_type)

        storage = StorageResults(table)
        storage.append(result)

    def get_last_result(self) -> pd.core.frame.DataFrame:
        raise NotImplementedError

    def report_trade(self, payload):
        self.trade_logs.create(**payload)
        commit()

    def reset(self):
        self.last_check.update(by_classifier_at=0)
        self.position.update(side="Zeroed", size=0.0)
        self.trade_logs.clear()
        commit()


class TradeLog(db.Entity):
    monitor = Optional(lambda: Monitor)
    signal_generated = Optional(str)
    signal_interpreted = Optional(str)
    timestamp = Optional(int)
    price = Optional(float)
    fee = Optional(float)  # base_asset units
    quote_amount = Optional(float)


class Operation(db.Entity, AttributeUpdater):
    name = Required(str, unique=True)
    monitors = Set(Monitor, cascade_delete=True)
    mode = Required(str, default=modes.backtesting)
    wallet = Optional(Json)
    _setup = Required(Json)
#    _notifier = Required(Json)
#    _backtesting = Optional(Json)

    def setup(self):
        return Deserialize(name="setup").from_json(self._setup)

#    def notifier(self):
#        return Deserialize(name="notifier").from_json(self._notifier)

#    def backtesting(self):
#        return Deserialize(name="backtesting").from_json(self._backtesting)

    def reset(self):
        self.update(wallet=json.dumps(dict(USDT=1000.00)))

        for monitor in self.monitors:
            monitor.reset()

    def recreate_monitors(self, market_list: list):
        self.monitors.clear()
        is_master = True
        for market in market_list:
            self.monitors.create(
                is_master=is_master,
                _market=market.json(),
                position=Position(),
                last_check=LastCheck(by_classifier_at=0),
            )
            commit()
            is_master=False

    def list_of_active_monitors(self) -> list:
        monitors = [monitor for monitor in self.monitors if monitor.is_active]
        monitors.sort()
        return monitors


db.generate_mapping(create_tables=True)
