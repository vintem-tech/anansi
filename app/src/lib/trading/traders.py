""" The needed classes in order to run operations; In other words, here
are the objects' representation which, when convenientally combined each
other, will periodically perform market analyzes (including triggering
orders and updating records in a database) or simulate trading operations
against historical data (backtestings).
"""

import time

import pendulum

from ...config.messages import TradingMonitor
from ...exceptions import TraderError
from ...repositories.sql_app.models import Operation
from ..notifier import OperationalNotifier
from .analyzers.classifiers import Classifier
from .analyzers.stoploss import StopLoss
from .order_handler import OrderHandler

messages = TradingMonitor()

class SingleTrader:
    """Capable of periodically performing a classification analysis
    (buy/sell/stop) on a market. A trader must have at least 4 class'
    attributes:

        - An operational setup and:
        - A classifier analyser;
        - A stoploss analyser;
        - A notifier manager.
    """

    def __init__(self, operation: Operation):
        self.operation = operation
        self.setup = operation.operational_setup()
        self.classifier = Classifier(operation)
        self.stoploss = StopLoss(operation)
        self.notifier = OperationalNotifier(operation)
        self.order_handler = OrderHandler(operation)
        self.now: int = None  # Datetime (seconds UTC timestamp)

    def _classifier_analysis(self):
        result = self.classifier.execution_pipeline(at_time=self.now)
        self.order_handler.evaluate(result)
    
    def _stoploss_analysis(self):
        result = self.stoploss.execution_pipeline(at_time=self.now)
        self.order_handler.evaluate(result)

    def _start(self):
        self.now = pendulum.now("UTC").int_timestamp
        if self.setup.backtesting.is_on:
            self.operation.reset()
            self.now = self.classifier.initial_backtesting_now()

        self.notifier.debug(messages.initial(self.operation.id, self.setup))
        self.operation.update(is_running=True)

    def _forward_step(self):
        step = (
            self.stoploss.step
            if self.stoploss.is_activated()
            else
            self.classifier.time_until_next_closed_candle()
        )
        self.notifier.debug(messages.time_monitoring(self.now, step))

        if self.setup.backtesting.is_on:
            self.now += step
            if self.now >= self.classifier.final_backtesting_now():
                self.operation.update(is_running=False)

        else:
            time.sleep(step)
            self.now = (pendulum.now(tz="UTC")).int_timestamp

    def run(self):
        self._start()
        while self.operation.is_running:
            try:
                self._stoploss_analysis()
                self._classifier_analysis()
                self._forward_step()

            except TraderError as err:
                self.notifier.error(err)
                time.sleep(300)  # 5 min cooldown

        self.notifier.debug(messages.final(self.operation.id))
