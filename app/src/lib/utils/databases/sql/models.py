import json

import pandas as pd
from pony.orm import Database, Json, Optional, Required, Set, commit, sql_debug

from .....config.settings import system_settings
from .....config.setups import initial_wallet
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
    position = Required(Position, cascade_delete=True)
    last_check = Required(LastCheck, cascade_delete=True)
    is_active = Required(bool, default=True)
    is_master = Required(bool, default=False)
    ticker_ = Required(Json)

    def ticker(self):
        return Ticker(**json.loads(self.ticker_))

    def save_result(self, result_type: str, result: pd.core.frame.DataFrame):
        ticker = self.ticker()
        table = "{}_{}_{}_{}".format(
            self.operation.name,
            self.operation.broker,
            ticker.symbol,
            result_type,
        )
        storage = StorageResults(table)
        storage.append(result)

    def get_last_result(self) -> pd.core.frame.DataFrame:
        raise NotImplementedError

    def reset(self):
        self.last_check.update(by_classifier_at=0)
        self.position.update(side="zeroed", size=0.0)
        commit()


class Operation(db.Entity, AttributeUpdater):
    name = Required(str, unique=True)
    broker = Required(str)
    monitors = Set(Monitor, cascade_delete=True)
    mode = Required(str, default=modes.backtesting)
    setup_ = Required(Json)
    orders = Set(lambda: Order, cascade_delete=True)

    @staticmethod
    def create(name: str, tickers_list: list, setup: json):
        raise NotImplementedError

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

    def quotes_list(self) -> list:
        return [
            monitor.ticker().quote
            for monitor in self.list_of_active_monitors()
        ]

    def save_order(self, order: dict):
        order.update(
            from_=json.dumps(order["from_"]), to=json.dumps(order["to"])
        )
        self.orders.create(**order)
        commit()


class RealTradingOperation(Operation):
    status = Optional(str)

    @staticmethod
    def create(name: str, tickers_list: list, setup: json):
        raise NotImplementedError


class BackTestingOperation(Operation):
    wallet = Optional(Json)
    fraction_complete = Optional(float)

    @staticmethod
    def create(name: str, broker:str, tickers_list: list, setup: json):
        operation = BackTestingOperation(
            name=name,
            broker=broker,
            setup_=setup,
        )
        commit()

        operation.recreate_monitors(tickers_list)
        operation.reset()

        return BackTestingOperation[operation.id]

    def reset(self):
        self.orders.clear()
        self.update(wallet=json.dumps(initial_wallet))
        self.reset_monitors()


class Order(db.Entity):
    operation = Optional(Operation)

    test_order = Optional(bool)
    by_stop = Optional(bool, default=False)
    order_type = Optional(str)
    leverage = Optional(float)

    timestamp = Optional(int)
    id_by_broker = Optional(str)

    from_ = Optional(Json)
    to = Optional(Json)

    signal = Optional(str)
    price = Optional(float)
    quantity = Optional(float)
    fulfilled = Optional(bool)
    fee = Optional(float)
    warnings = Optional(str)


db.generate_mapping(create_tables=True)
