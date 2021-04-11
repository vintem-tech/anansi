import pandas as pd

# from ...log import Notifier
from ..marketdata.operators.classifiers import get_classifier
from ..tools.time_handlers import time_frame_to_seconds
from ..utils.databases.sql.models import Monitor, Operation
from ..utils.databases.sql.schemas import (
    ClassifierPayLoad,
    DateTimeType,
    OperationalModes,
    Order,
    Sides,
)
from .order_handler import OrderHandler

modes = OperationalModes()
sides = Sides()


class Analyzer:
    def __init__(self, monitor: Monitor):
        self.monitor = monitor
        self.setup = monitor.operation.setup()
        payload = ClassifierPayLoad(
            market=monitor.market(),
            classifier=self.setup.classifier,
            backtesting=bool(monitor.operation.mode == modes.backtesting),
        )
        self.classifier = get_classifier(payload)
        self.was_updated = False
        self.now: int = None
        self.order = Order()

    def _is_a_new_analysis_needed(self) -> bool:
        last_check = self.monitor.last_check.by_classifier_at
        step = time_frame_to_seconds(self.setup.classifier.setup.time_frame)
        return bool(self.now >= last_check + step)

    def _evaluate_side(self, score: float) -> str:
        side = (
            sides.long
            if score > self.setup.score_that_triggers_long_side
            else sides.short
            if score < self.setup.score_that_triggers_short_side
            and self.setup.allow_naked_sells
            else sides.zeroed
        )
        return side

    def populate_order(self, result: pd.core.frame.DataFrame):
        self.order.score = result.score
        self.order.to_side = self._evaluate_side(result.Score)
        self.order.test_order = bool(
            self.monitor.operation.mode == modes.test_trading
        )
        self.order.timestamp = self.now
        self.order.order_type = self.setup.default_order_type
        self.order.from_side = self.monitor.position.side

    def check_at(self, desired_datetime: DateTimeType):
        self.was_updated = False
        self.now = desired_datetime
        if self._is_a_new_analysis_needed():
            self.was_updated = True
            result = self.classifier.get_restult_at(desired_datetime)
            self.monitor.save_result("classifier", result)
            self.monitor.last_check.update(by_classifier_at=self.now)
            self.populate_order(result)

    def save_and_report_trade(self):
        self.monitor.report_trade(payload=self.order.dict())


class Trader:
    def __init__(self, operation: Operation):
        monitors = operation.list_of_active_monitors()
        self.analyzers = [Analyzer(monitor) for monitor in monitors]
        self.order_handler = OrderHandler(
            bases_symbols=operation.setup().bases_symbols
        )
        # self.stop_loss = [StopLoss(monitor) for monitor in monitors]

    def check_at(self, desired_datetime: DateTimeType):
        # for stop in self.stop_loss:
        #    stop.check_at(desired_datetime)

        for analyzer in self.analyzers:
            analyzer.check_at(desired_datetime)

        self.order_handler.process(
            analyzers=[
                analyzer for analyzer in self.analyzers if analyzer.was_updated
            ]
        )
