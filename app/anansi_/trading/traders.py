import time
from threading import Thread

import pendulum

from ..notifiers.notifiers import get_notifier
from ..tools.formatting import text_in_lines_from_dict
from ..tools.serializers import Deserialize
from ..tools.time_handlers import ParseDateTime
from .classifiers import get_classifier
from .models import Operation
from .order_handler import get_order_handler


class DefaultTrader(Thread):
    def __init__(self, operation: Operation):
        self.operation = operation
        self.setup = Deserialize(name="setup").from_json(operation.setup)

        self.classifier = get_classifier(
            classifier_name=self.setup.classifier_name,
            market=self.setup.market,
            setup=self.setup.classifier_setup,
            backtesting=self.setup.backtesting
        )

        self.notifier = get_notifier(broadcasters=self.setup.broadcasters)
        self.order_handler = get_order_handler(operation)
        self.now: int = None  # Datetime (seconds UTC timestamp)
        super().__init__()

    def _start(self):
        self.now = pendulum.now("UTC").int_timestamp
        if self.setup.backtesting:
            self.operation.reset()
            self.now = self.classifier.initial_backtesting_now()

        if self.setup.debbug:
            setup_str = text_in_lines_from_dict(self.setup._asdict())
            msg = "Starting Anansi. Your operation id is {}\n\n{}".format(
                self.operation.id, setup_str
            )
            self.notifier.debbug(msg)
        self.operation.update(is_running=True)

    def _classifier_analysis(self):
        new_candle = bool(
            self.now >= (
                self.operation.last_check.by_classifier_at +
                self.classifier.time_frame_total_seconds))

        if new_candle:
            result = self.classifier.restult_at(desired_datetime=self.now)
            self.operation.update_current_result(result)
            self.operation.last_check.update(by_classifier_at=self.now)

    def analysis_pipeline(self) -> None:
        self._classifier_analysis()
        self.order_handler.proceed()

    def _forward_step(self):
        debbug = self.setup.debbug
        if self.setup.backtesting:
            self.now += self.classifier.time_frame_total_seconds()

            if self.now > self.classifier.final_backtesting_now():
                self.operation.update(is_running=False)

        else:
            sleep_time = self.classifier.time_until_next_closed_candle + 10
            if debbug:
                utc_now = ParseDateTime(
                    (pendulum.now(tz="UTC")).int_timestamp
                ).from_timestamp_to_human_readable()

                msg = """Time now (UTC) = {}\nSleeping {} s.""".format(
                    utc_now, sleep_time
                )
                self.notifier.debbug(msg)

            time.sleep(sleep_time)
            self.now = (pendulum.now(tz="UTC")).int_timestamp

    def run(self):
        self._start()
        while self.operation.is_running:
            #try:
            self.analysis_pipeline()
            self._forward_step()

            #except Exception as e:
                #self.notifier.error(e)
                #time.sleep(3600)  # 1 hour cooldown

        final_msg = "Op. {} finalized!".format(self.operation.id)
        self.notifier.error(final_msg)

    def run_in_background(self):
        self.start()
