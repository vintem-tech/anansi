from ...log import Notifier
from ..utils.databases.sql.models import Monitor, Operation
from ..utils.databases.sql.schemas import DateTimeType, Signals

sig = Signals()


class Analyzer:
    def __init__(self, monitor: Monitor):
        self.monitor = monitor


class StopLoss:
    def __init__(self, monitor: Monitor):
        self.monitor = monitor


class OrderHandler:
    def __init__(self, operation: Operation):
        self.operation = operation


class Trader:
    def __init__(self, operation: Operation):
        self.notifier = Notifier(operation)
        self.order = OrderHandler(operation)
        self.monitors = operation.list_of_active_monitors()
        self.analyzers = [Analyzer(monitor) for monitor in self.monitors]
        self.stop_loss = [StopLoss(monitor) for monitor in self.monitors]

    def check_at(self, desired_datetime: DateTimeType):
        for stop in self.stop_loss:
            stop.check_at(desired_datetime)

        for analyzer in self.analyzers:
            analyzer.check_at(desired_datetime)

        self.order.handler(
            analyzers=[
                analyzer
                for analyzer in self.analyzers
                if analyzer.signal != sig.Zeroed
            ]
        )
