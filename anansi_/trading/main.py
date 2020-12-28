import pandas as pd
import pendulum
import time
from .schemas import OpSetup, BaseModel
from .classifiers import classifier
from .order_handler import order_handler
from ..share.tools import short_hash_from
from ..share.storage import StorageResults
from ..share.notifiers import Notifier


class Operation:
    def __init__(self, setup: OpSetup):
        self.setup = setup
        self.id = short_hash_from(setup)
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
        self.classifier = classifier(**operation.setup.classifier_payload)
        self.order_handler = order_handler(operation)
        self.is_running: bool = False
        self.now: int = None  # Datetime (seconds UTC timestamp)
        self.notifier = Notifier(broadcasters=operation.setup.broadcasters)
        self.notifier.show_header = False

    def _start(self):
        debbug = self.operation.setup.debbug
        self.now = (
            self.classifier.initial_backtesting_now()
            if self.operation.setup.backtesting
            else pendulum.now("UTC").int_timestamp
        )
        self.is_running = True
        if debbug: self.notifier.debbug(msg="Starting Anansi")
        
    def _classifier_analysis(self):
        result = self.classifier.restult_at(desired_datetime=self.now)
        self.operation.update(result)

    def analysis_pipeline(self) -> None:
        self._classifier_analysis()
        self.order_handler.proceed()

    # TODO: Timesleep para o trade real
    def forward_step(self):
        if self.operation.setup.backtesting:
            self.now += self.classifier.time_frame_total_seconds

            if self.now > self.classifier.final_backtesting_now():
                self.is_running = False
        
        else:
            sleep_time = self.classifier.time_until_next_closed_candle + 5
            time.sleep(sleep_time)

    def run(self):
        self._start()
        while self.is_running:
            try:
                self.analysis_pipeline()
                self.forward_step()
            
            except Exception as e:
                self.notifier.error(e)
