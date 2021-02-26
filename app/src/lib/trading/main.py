""" Deve lidar com o monitoramento periódicos de mercados, performando as operações """

from ...config.messages import TradingMonitor
from ...exceptions import TraderError
from ...repositories.sql_app.models import Monitor
from ...repositories.sql_app.schemas import Signals as sig
from ..notifier import OperationalNotifier
from .analyzers.classifiers import Classifier
from .analyzers.stoploss import StopLoss
from .order_handler import OrderHandler

messages = TradingMonitor()

class Signal:
    def __init__(self, from_side: str, to_side: str, by_stop: bool):
        self.from_side = from_side.capitalize()
        self.to_side = to_side.capitalize()
        self.by_stop = by_stop

    def generate(self):
        if self.from_side == self.to_side:
            return sig.hold

        if self.from_side == "Zeroed":
            if self.to_side == "Long":
                return sig.buy
            if self.to_side == "Short":
                return sig.naked_sell

        if self.from_side == "Long":
            if self.to_side == "Zeroed":
                if self.by_stop:
                    return sig.long_stopped
                return sig.sell
            if self.to_side == "Short":
                return sig.double_naked_sell

        if self.from_side == "Short":
            if self.to_side == "Zeroed":
                if self.by_stop:
                    return sig.short_stopped
                return sig.buy
            if self.to_side == "Long":
                return sig.double_buy

class Monitor:
    def __init__(self, operation: Operation):
        self.operation = operation
        self.setup = operation.operational_setup()
        self.classifier = Classifier(operation)
        self.stoploss = StopLoss(operation)
        self.notifier = OperationalNotifier(operation)
        self.order_handler = OrderHandler(operation)


class Trader:
    def __init__(self, monitors:list, backtesting=True):
        self.monitors = [(operation) for operation in operations]
        self.backtesting = backtesting

    def start(self):
        raise NotImplementedError
    
    def stop(self):
        raise NotImplementedError
    
    def run(self):
        self.start()
        while True:
            pass