import pandas as pd
import pendulum
import time
from ..sql_app.schemas import OpSetup  # , BaseModel
from .classifiers import get_classifier
from .order_handler import get_order_handler
from ..tools.hashes import hash_from_an_object
from ..tools.time_handlers import ParseDateTime
from ..storage.storage import StorageResults
from ..notifiers.notifiers import get_notifier


class Operation:
    def __init__(self, setup: OpSetup):
        self.setup = setup
        self.id = hash_from_an_object(setup)
        self.current_result = pd.DataFrame()
        self.storage = StorageResults(table=self.id, database="results")

    def update(self, result: pd.core.frame.DataFrame) -> None:
        self.current_result[list(result.columns)] = result

    def stoploss_result(self):
        raise NotImplementedError

    def save_current_result(self) -> bool:
        self.storage.append(self.current_result)

    def get_last_result(self) -> pd.core.frame.DataFrame:
        raise NotImplementedError


class DefaultTrader:
    def __init__(self, operation: Operation):
        self.operation = operation

        self.classifier = get_classifier(**operation.setup.classifier_payload)
        self.notifier = get_notifier(broadcasters=operation.setup.broadcasters)
        self.order_handler = get_order_handler(operation)

        self.is_running: bool = False
        self.now: int = None  # Datetime (seconds UTC timestamp)

    def _start(self):
        debbug = self.operation.setup.debbug
        self.now = (
            self.classifier.initial_backtesting_now()
            if self.operation.setup.backtesting
            else pendulum.now("UTC").int_timestamp
        )
        self.is_running = True
        if debbug:
            self.notifier.debbug(msg="Starting Anansi")

    def _classifier_analysis(self):
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
                self.notifier.debbug("Time now (UTC) = {}".format(utc_now))
                self.notifier.debbug("Sleeping {} s.".format(sleep_time))
            time.sleep(sleep_time)

    def run(self):
        self._start()
        while self.is_running:
            try:
                self.analysis_pipeline()
                self.forward_step()

            except Exception as e:
                self.notifier.error(e)
                time.sleep(3600)
