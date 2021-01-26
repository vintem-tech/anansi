import time
from threading import Thread

import pendulum

from ..notifiers.notifiers import get_notifier
from ..tools.formatting import text_in_lines_from_dict
from ..tools.serializers import Deserialize
from ..tools.time_handlers import ParseDateTime
from .classifiers import get_classifier
from .stoploss import get_stop
from .models import Operation
from .order_handler import get_order_handler


class DefaultTrader(Thread):
    def __init__(self, operation: Operation):
        self.operation = operation
        self.setup = Deserialize(name="setup").from_json(operation.setup)
        self.classifier = get_classifier(operation)
        self.stoploss = get_stop(operation)
        self.order_handler = get_order_handler(operation)
        self.notifier = get_notifier(broadcasters=self.setup.broadcasters)
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

    def _stop_analysis(self):
        verify_stoploss = bool(
            self.operation.position.side != "Zeroed" and self.setup.stop_is_on
        )
        if verify_stoploss:
            self.stoploss.verify()
            self.operation.last_check.update(by_stop_loss_at=self.now)
        else:
            pass

    def _classifier_analysis(self):
        new_candle = bool(
            self.now
            >= (
                self.operation.last_check.by_classifier_at
                + self.classifier.time_frame_total_seconds()
            )
        )
        if new_candle:
            result = self.classifier.restult_at(desired_datetime=self.now)
            self.operation.update_current_result(result)
            self.operation.last_check.update(by_classifier_at=self.now)

    def analysis_pipeline(self) -> None:
        self._stop_analysis()
        self._classifier_analysis()
        self.order_handler.proceed()

    def _forward_step(self):
        debbug = self.setup.debbug
        stoploss_monitoring = bool(
            self.operation.position.side != "Zeroed" and self.setup.stop_is_on
        )
        if self.setup.backtesting:
            add_to_now = (
        # Aqui há um inconsistência, já que ele pode desarmar por stop e "pular" um candle.
                self.stoploss.time_frame_total_seconds()
                if stoploss_monitoring
                else self.classifier.time_frame_total_seconds()
            )
            self.now += add_to_now

            if self.now > self.classifier.final_backtesting_now():
                self.operation.update(is_running=False)

        else:
            if stoploss_monitoring:
                sleep_time = self.stoploss.sleep_time()
            else:
                sleep_time = (
                    self.classifier.time_until_next_closed_candle() + 10
                )
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
            # try:
            self.analysis_pipeline()
            self._forward_step()

            # except Exception as e:
            # self.notifier.error(e)
            # time.sleep(3600)  # 1 hour cooldown

        final_msg = "Op. {} finalized!".format(self.operation.id)
        self.notifier.error(final_msg)

    def run_in_background(self):
        self.start()
