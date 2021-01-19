import time
from threading import Thread

import pandas as pd
import pendulum
from ..notifiers.notifiers import get_notifier
from ..sql_app.schemas import OpSetup
from ..tools.time_handlers import ParseDateTime
from ..tools.formatting import text_in_lines_from_dict
from ..tools.serializers import Deserialize
from .classifiers import get_classifier
from .order_handler import get_order_handler
from .models import Operation

class DefaultTrader(Thread):
    def __init__(self, operation:Operation):
        self.operation = operation
        self.setup = Deserialize(name="setup").from_json(operation.setup)

        self.classifier = get_classifier(
            classifier_name=self.setup.classifier_name,
            market=self.setup.market,
            time_frame=self.setup.time_frame,
            setup=self.setup.classifier_setup)

        self.notifier = get_notifier(broadcasters=operation.setup.broadcasters)
        self.order_handler = get_order_handler(operation)
        self.now: int = None  # Datetime (seconds UTC timestamp)
        super().__init__()

    def _start(self):
        debbug = self.operation.setup.debbug
        self.now = (
            self.classifier.initial_backtesting_now()
            if self.operation.setup.backtesting
            else pendulum.now("UTC").int_timestamp
        )
        self.is_running = True
        if debbug:
            setup_str = text_in_lines_from_dict(self.operation.setup.dict())
            msg = "Starting Anansi. Your operation id is {}\n\n{}".format(
                self.operation.id, setup_str
            )
            self.notifier.debbug(msg)

    def _classifier_analysis(self):
        # TODO: Só realizar esta analise se já existir um candle aberto...
        result = self.classifier.restult_at(desired_datetime=self.now)
        self.operation.update(result)

    def analysis_pipeline(self) -> None:
        self._classifier_analysis()
        self.order_handler.proceed()

    def forward_step(self):
        if self.operation.setup.backtesting:
            self.now += self.classifier.time_frame_total_seconds

            if self.now > self.classifier.final_backtesting_now():
                self.is_running = False

        else:
            sleep_time = self.classifier.time_until_next_closed_candle + 30
            if self.operation.setup.debbug:
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
        while self.is_running:
            try:
                self.analysis_pipeline()
                self.forward_step()

            except Exception as e:
                self.notifier.error(e)
                time.sleep(3600)  # 1 hour cooldown

        final_msg = "Op. {} finalized!".format(self.operation.id)
        self.notifier.error(final_msg)

    def run_in_background(self):
        self.start()
