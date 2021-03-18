import pandas as pd

from ...log import Notifier
from ..marketdata.operators.classifiers import get_classifier
from ..tools.time_handlers import time_frame_to_seconds
from ..utils.databases.sql.models import Monitor, Operation
from ..utils.databases.sql.schemas import (
    ClassifierPayLoad,
    DateTimeType,
    OperationalModes,
    Signals,
)
from .order_handler import get_order_handler, Signal

sig = Signals()
mode = OperationalModes()


class Analyzer:
    def __init__(self, monitor: Monitor):
        self.monitor = monitor
        self.setup = monitor.operation.setup()
        payload = ClassifierPayLoad(
            market=monitor.market(),
            classifier=self.setup.classifier,
            backtesting=bool(monitor.operation.mode == mode.backtesting),
        )
        self.classifier = get_classifier(payload)
        self.result = pd.DataFrame()
        self.now: int = None
        self.signal: str = sig.hold

    def _is_a_new_analysis_needed(self) -> bool:
        last_check = self.monitor.last_check.by_classifier_at
        step = time_frame_to_seconds(self.setup.classifier.setup.time_frame)
        return bool(self.now >= last_check + step)

    def check_for_signal(self):
        score = self.result.score
        side = (
            "Long"
            if score > 0.3
            else "Short"
            if score < -0.3 and self.setup.allow_naked_sells
            else "Zeroed"
        )
        self.signal = Signal(
            from_side=self.monitor.position.side, to_side=side
        ).generate()

    def check_at(self, desired_datetime: DateTimeType):
        self.signal = sig.hold
        self.now = desired_datetime
        if self._is_a_new_analysis_needed():
            self.result = self.classifier.get_restult_at(desired_datetime)
            self.monitor.save_result("classifier", self.result)
            self.monitor.last_check.update(by_classifier_at=self.now)
            self.check_for_signal()


# class StopLoss:
#    def __init__(self, monitor: Monitor):
#        self.monitor = monitor


# class OrderHandler:
#    def __init__(self, operation: Operation):
#        self.operation = operation


class Trader:
    def __init__(self, operation: Operation):
        self.notifier = Notifier(operation)
        self.order_handler = get_order_handler(operation)
        self.monitors = operation.list_of_active_monitors()
        self.analyzers = [Analyzer(monitor) for monitor in self.monitors]

    #        self.stop_loss = [StopLoss(monitor) for monitor in self.monitors]

    def check_at(self, desired_datetime: DateTimeType):
        #        for stop in self.stop_loss:
        #            stop.check_at(desired_datetime)

        for analyzer in self.analyzers:
            analyzer.check_at(desired_datetime)

        self.order_handler.process(
            analyzers=[
                analyzer
                for analyzer in self.analyzers
                if analyzer.signal != sig.hold
            ]
        )
