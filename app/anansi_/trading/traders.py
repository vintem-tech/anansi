""" The needed classes in order to run operations; In other words, here
are the objects' representation which, when convenientally combined each
other, will periodically perform market analyzes (including triggering
orders and updating records in a database) or simulate trading operations
against historical data (backtestings).
"""

import time

import pendulum

from ..config.defaults import Messages
from ..notifiers.notifiers import Notifier
from .analyzers import Classifier, StopLoss
from .models import Operation

messages = Messages()

class Trader:
    """Capable of periodically performing a classification analysis
    (buy/sell/stop) on a market. A trader must have at least 4 class'
    attributes:

        - An operational setup and:
        - A classifier;
        - A stoploss manager;
        - A notifier.

    the last 3 must be instantiated for the given operation.
    """

    def __init__(self, operation: Operation):
        self.operation = operation
        self.setup = operation.operational_setup()
        self.classifier = Classifier(operation)
        self.stoploss = StopLoss(operation)
        self.notifier = Notifier(operation)
        self.now: int = None  # Datetime (seconds UTC timestamp)

    def _start(self):
        self.now = pendulum.now("UTC").int_timestamp
        if self.setup.backtesting.is_on:
            self.operation.reset()
            self.now = self.classifier.initial_backtesting_now()

        self.notifier.debbug(messages.initial(self.operation.id, self.setup))
        self.operation.update(is_running=True)

    def _forward_step(self):
        step = (
            self.stoploss.time_until_next_closed_candle()
            if self.stoploss.is_on()
            else
            self.classifier.time_until_next_closed_candle()
        )
        self.notifier.debbug(messages.time_monitoring(self.now, step))

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
                self.stoploss.analyze(at_time=self.now)
                self.classifier.analyze(at_time=self.now)
                self._forward_step()

            except Exception as e:
                self.notifier.error(e)
                time.sleep(600)  # 10 min cooldown

        self.notifier.debbug(messages.final(self.operation.id))