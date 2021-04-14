import json

import pandas as pd
from pony.orm import Database, Json, Optional, Required, Set, commit, sql_debug

from .....config.settings import system_settings
from .....config.setups import initial_wallet
from ....utils.schemas import OperationalModes
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
    side = Required(str, default="Zeroed")
    size = Required(float, default=0.0)  # by quote
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
    market_ = Required(Json)
    position = Required(Position, cascade_delete=True)
    last_check = Required(LastCheck, cascade_delete=True)
    orders = Set(lambda: Order, cascade_delete=True)

    def market(self):
        return Deserialize(name="market").from_json(self.market_)

    def save_result(self, result_type: str, result: pd.core.frame.DataFrame):
        market = self.market()
        table = "{}_{}_{}_{}".format(
            self.operation.name,
            market.broker_name,
            market.ticker_symbol,
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
        self.position.update(side="Zeroed", size=0.0)
        self.orders.clear()
        commit()


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


class Operation(db.Entity, AttributeUpdater):
    name = Required(str, unique=True)
    monitors = Set(Monitor, cascade_delete=True)
    # mode = Required(str, default=modes.backtesting)
    # wallet = Optional(Json)  # Useful on backtesting scenarios
    setup_ = Required(Json)

    def setup(self):
        return Deserialize(name="setup").from_json(self.setup_)

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
            monitor.market().base_symbol
            for monitor in self.list_of_active_monitors()
        ]


class RealTradingOperation(Operation):
    mode = Required(str, default=modes.real_trading)


class BackTestingOperation(Operation):
    mode = Required(str, default=modes.backtesting)
    wallet = Optional(Json)

    def reset(self):
        self.update(wallet=json.dumps(initial_wallet))
        self.reset_monitors()


db.generate_mapping(create_tables=True)
