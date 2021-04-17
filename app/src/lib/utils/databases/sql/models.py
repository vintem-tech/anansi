import json

import pandas as pd
from pony.orm import Database, Json, Optional, Required, Set, commit, sql_debug

from .....config.settings import system_settings
from .....config.setups import (
    initial_wallet,
    OperationalSetup,
    BinanceMonitoring,
)
from ....utils.schemas import OperationalModes, Ticker
from ...tools.serializers import Deserialize
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


class Position(db.Entity, AttributeUpdater):
    monitor = Optional(lambda: Monitor)  # Foreing key
    side = Required(str, default="zeroed")
    by_score = Required(float, default=0.0)
    size = Required(float, default=0.0)
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
    ticker_ = Required(Json)
    position = Required(Position, cascade_delete=True)
    last_check = Required(LastCheck, cascade_delete=True)
    orders = Set(lambda: Order, cascade_delete=True)

    def ticker(self):
        return Ticker(**json.loads(self.ticker_))

    def save_result(self, result_type: str, result: pd.core.frame.DataFrame):
        ticker = self.ticker()
        table = "{}_{}_{}_{}".format(
            self.operation.name,
            ticker.broker_name,
            ticker.ticker_symbol,
            result_type,
        )
        storage = StorageResults(table)
        storage.append(result)

    def get_last_result(self) -> pd.core.frame.DataFrame:
        raise NotImplementedError

    def save_trading_log(self, payload: dict):
        self.orders.create(**payload)
        commit()

    def reset(self):
        self.last_check.update(by_classifier_at=0)
        self.position.update(side="zeroed", size=0.0)
        self.orders.clear()
        commit()


class Operation(db.Entity, AttributeUpdater):
    name = Required(str, unique=True)
    monitors = Set(Monitor, cascade_delete=True)
    mode = Required(str, default=modes.backtesting)
    # wallet = Optional(Json)  # Useful on backtesting scenarios
    setup_ = Required(Json)

#    def setup(self):
#        return OperationalSetup(**json.loads(self.setup_))
    
    def setup(self):
        return Deserialize(name="setup").from_json(self.setup_)

    def recreate_monitors(self, tickers_list: list):
        self.monitors.clear()
        is_master = True
        for ticker in tickers_list:
            self.monitors.create(
                is_master=is_master,
                ticker_=ticker.json(),
                position=Position(),
                last_check=LastCheck(by_classifier_at=0),
            )
            commit()
            is_master = False

    def reset_monitors(self):
        for monitor in self.monitors:
            monitor.reset()

    def list_of_active_monitors(self) -> list:
        monitors = [monitor for monitor in self.monitors if monitor.is_active]
        monitors.sort()
        return monitors

    def bases_symbols(self) -> list:
        return [
            monitor.ticker().base_symbol
            for monitor in self.list_of_active_monitors()
        ]


class RealTradingOperation(Operation):
    status = Optional(str)


class BackTestingOperation(Operation):
    wallet = Optional(Json)
    fraction_complete = Optional(float)

    def reset(self):
        self.update(wallet=json.dumps(initial_wallet))
        self.reset_monitors()


def create_backtesting_operation(
    name: str,
    tickers_list = BinanceMonitoring().tickers(),
    setup: json = OperationalSetup().json(),
) -> Operation:

    operation = BackTestingOperation(
        name=name,
        setup_=setup,
    )
    commit()

    operation.recreate_monitors(tickers_list)
    operation.reset()

    return BackTestingOperation[operation.id]


class Order(db.Entity):
    monitor = Optional(lambda: Monitor)
    test_order = Optional(bool)
    id_by_broker = Optional(str)
    timestamp = Optional(int)
    order_type = Optional(str)
    from_side = Optional(str)
    to_side = Optional(str)
    score = Optional(float)
    leverage = Optional(float)
    generated_signal = Optional(str)
    interpreted_signal = Optional(str)
    price = Optional(float)
    quantity = Optional(float)
    fulfilled = Optional(bool)
    fee = Optional(float)
    warnings = Optional(str)


db.generate_mapping(create_tables=True)
