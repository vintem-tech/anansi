import pandas as pd
from tabulate import tabulate

from ..marketdata.operators.classifiers import get_classifier
from ..utils.databases.sql.models import Monitor, Operation
from ..utils.schemas import DateTimeType, OperationalModes, Order, Sides
from ..utils.tools.time_handlers import (datetime_as_integer_timestamp,
                                         time_frame_to_seconds)
from .orderflow import OrderHandler

modes = OperationalModes()
sides = Sides()


class Analyzer:
    def __init__(self, monitor: Monitor):
        self.monitor = monitor
        self.setup = monitor.operation.setup()
        self.classifier = get_classifier(
            name=self.setup.classifier.name,
            ticker=monitor.ticker(),
            setup=self.setup.classifier.setup,
            backtesting=bool(monitor.operation.mode == modes.backtesting),
        )
        self.was_updated = False
        self.current_timestamp: int = None
        self.order = Order()
        self.result = pd.DataFrame()

    def _is_a_new_analysis_needed(self) -> bool:
        last_check = self.monitor.last_check.by_classifier_at
        step = time_frame_to_seconds(self.setup.classifier.setup.time_frame)
        return bool(self.current_timestamp >= last_check + step)

    def _evaluate_side(self) -> str:
        score = self.order.to.score
        if score > self.setup.trading.score_that_triggers_long_side:
            return sides.long

        if score < self.setup.trading.score_that_triggers_short_side:
            return sides.short
        return sides.zeroed

    def _reset(self):
        self.was_updated = False
        self.order.test_order = bool(
            self.monitor.operation.mode == modes.test_trading
        )
        self.order.order_type = self.setup.trading.default_order_type
        self.order.leverage = self.setup.trading.leverage
        self.order.signal = 'reset'
        self.order.fulfilled = False
        self.order.warnings = str()

    def _refresh_result(self):
        self.result = self.classifier.get_restult_at(self.current_timestamp)
        self.monitor.save_result("classifier", self.result)

    def _fill_the_order(self):        
        self.order.timestamp = self.current_timestamp

        self.order.from_.score = self.monitor.position.by_score
        self.order.from_.side = self.monitor.position.side

        self.order.to.score = self.result.Score.tail(1).item()
        self.order.to.side = self._evaluate_side()

    def _update(self):
        self.monitor.last_check.update(by_classifier_at=self.current_timestamp)
        self.was_updated = True

    def check_at(self, desired_datetime: DateTimeType):
        self._reset()
        self.current_timestamp = datetime_as_integer_timestamp(
            desired_datetime
        )
        if self._is_a_new_analysis_needed():
            self._refresh_result()
            self._fill_the_order()
            self._update()

# Migrate to a specific class

    def _update_position(self):
        order = self.order
        self.monitor.position.update(
            side = order.to.side,
            by_score = order.to.score,
            size = order.quantity,
            enter_price = order.price,
            timestamp = order.timestamp,
            exit_reference_price = order.price,
        )

    def _report_and_notify(self):
        self.monitor.save_trading_log(payload=self.order.dict())
        print(self.order.dict())
        print(" ")

    def report_and_notify(self):
        if self.order.fulfilled:
            self._update_position()
            self._report_and_notify()

        if self.monitor.operation.mode == modes.backtesting:
            self._report_and_notify()

    def debug_message_items(self) -> list:
        return [
            self.monitor.ticker().ticker_symbol,
            self.order.to.score,
            self.monitor.position.side
        ]

class Trader:
    def __init__(self, operation: Operation):
        monitors = operation.list_of_active_monitors()
        self.analyzers = [Analyzer(monitor) for monitor in monitors]
        self.order_handler = OrderHandler(
            bases_symbols=operation.bases_symbols()
        )
        # self.stop_loss = [StopLoss(monitor) for monitor in monitors]

    def report_and_notify(self):
        table = list()
        for analyzer in self.analyzers:
            if analyzer.was_updated:
                analyzer.report_and_notify()

            table.append(analyzer.debug_message_items())

        debbug_msg_ = tabulate(table, tablefmt="plain",floatfmt=".2f")
        print(debbug_msg_)

    def check_at(self, desired_datetime: DateTimeType):
        # for stop in self.stop_loss:
        #    stop.check_at(desired_datetime)

        updated_analyzers = list()
        for analyzer in self.analyzers:
            analyzer.check_at(desired_datetime)
            if analyzer.was_updated:
                updated_analyzers.append(analyzer)

        if updated_analyzers:
            self.order_handler.process(analyzers=updated_analyzers)
            self.report_and_notify()
