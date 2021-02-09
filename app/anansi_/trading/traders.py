import time
from threading import Thread

import pendulum

from ..notifiers.notifiers import get_notifier
from ..tools.formatting import text_in_lines_from_dict
from ..tools.serializers import Deserialize
from ..tools.time_handlers import ParseDateTime
from .classifiers import Classifier#, get_classifier
from .stoploss import get_stop
from .models import Operation
from .order_handler import get_order_handler


class DefaultTrader(Thread):
    def __init__(self, operation: Operation):
        self.operation = operation
        self.setup = Deserialize(name="setup").from_json(operation.setup)
        self.classifier = Classifier(operation)
        self.stoploss = get_stop(operation)

        # O notifier também poderia ser instanciado passando a operação. Assim,
        # resultados de logs (debbugs e/ou erros) poder ser apendados como
        # séries temporais no influxdb
        self.order_handler = get_order_handler(operation)
        
        self.notifier = get_notifier(broadcasters=self.setup.broadcasters)
        self.now: int = None  # Datetime (seconds UTC timestamp)
        self.step: int = None # Seconds
        super().__init__()

    def _start(self):
        self.now = pendulum.now("UTC").int_timestamp
        if self.setup.backtesting.is_on:
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
        self.step = self.classifier.time_until_next_closed_candle()
        verify_stoploss = bool(
            self.operation.position.side != "Zeroed" and self.setup.stop_is_on
        )
        if verify_stoploss:
            result = self.stoploss.result_at(desired_datetime=self.now)
            self.operation.save_result("stoploss", result)
            self.order_handler.proceed(
                at_time=self.now,
                analysis_result=result,
                by_stop=True,
            )
            self.operation.last_check.update(by_stop_loss_at=self.now)
            self.step = self.stoploss.time_until_next_closed_candle()

    def _classifier_analysis(self):
        last_check = self.operation.last_check.by_classifier_at
        step = self.classifier.time_frame_total_seconds()
        new_candle = bool(self.now >= last_check + step)

        if new_candle:
            result = self.classifier.restult_at(desired_datetime=self.now)
            self.operation.save_result("classifier", result)
            self.order_handler.proceed(
                at_time=self.now,
                analysis_result=result,
            )
            self.operation.last_check.update(by_classifier_at=self.now)

    def _forward_step(self):
        if self.setup.debbug:
            now = ParseDateTime(self.now).from_timestamp_to_human_readable()
            _step = ParseDateTime(self.step).from_timestamp_to_human_readable()
            msg = """Time now (UTC) = {}\nSleeping {} s.""".format(now, _step)
            self.notifier.debbug(msg)

        if self.setup.backtesting.is_on:
            self.now += self.step

        else:
            time.sleep(self.step)
            self.now = (pendulum.now(tz="UTC")).int_timestamp


    def run(self):
        self._start()
        while self.operation.is_running:
            # try:
            self._stop_analysis()
            self._classifier_analysis()
            self._forward_step()

            # except Exception as e:
            # self.notifier.error(e)
            # time.sleep(3600)  # 1 hour cooldown

        final_msg = "Op. {} finalized!".format(self.operation.id)
        self.notifier.debbug(final_msg)

    def run_in_background(self):
        self.start()

class OffSetRealTimeTresholdTrader:
    pass

