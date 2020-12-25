from typing import Union
import pandas as pd
from .schemas import Operation as OpSetup
from .classifiers import classifier
from .order_handler import OrderHandler
from ..share.tools import short_hash_from_obj


class Operation:
    def __init__(self, setup:OpSetup):
        self.setup = setup
        self.id = short_hash_from_obj(setup)
        self.current_result = self.get_last_result()

    def _reset_portfolio(self):
        quote = 0.0
        base = self.setup.initial_base_amount

        self.update_portfolio(quote, base)

    def _fetch_to_broker_portfolio(self):
        raise NotImplementedError

    def update_portfolio(self, quote: float, base: float) -> None:
        _quote = self.setup.market.quote_symbol
        _base = self.setup.market.base_symbol

        self.current_result[_quote] = quote
        self.current_result[_base] = base

    def classifier_result(self, result: pd.core.frame.DataFrame) -> None:
        self.current_result[list(result.columns)] = result

    def stoploss_result(self):
        raise NotImplementedError

    def save_current_result(self) -> bool:
        
        print(self.current_result)
        #pass

    def get_last_result(self) -> pd.core.frame.DataFrame:
        return pd.DataFrame()


class DefaultTrader:
    def __init__(self, operation:Operation):
        self.operation = operation
        self.classifier = classifier(**operation.setup.classifier_payload)
        self.order_handler = OrderHandler(operation)
        self.now = ""

    def _start(self):
        pass

    def analysis_pipeline(self) -> None:
        self.operation.classifier_result(
            result=self.classifier.restult_at(desired_datetime=self.now)
        )

        self.order_handler.proceed()
        self.operation.save_current_result()

    def forward_step(self):
        pass

    def run(self):
        self._start()
        while True:
            self.analysis_pipeline()
            self.forward_step()


"""
MODELO

A chave é a variável 'now'; em vez de criar uma lógica complexa, melhor vir
através do input do usuário. No cliente (que vai performar, temporariamente, o
trade BTCUSDT), basta chamar o 'oldest_open_time' e o 'newest_open_time' do
banco


   def _start(self):
        self.op.if_no_assets_fill_them()
        self._now = pendulum.now("UTC").int_timestamp
        self.op.update(status=STAT.Running)

        if self.op.mode == MODE.BackTesting:
            self.op.reset()

            # TODO: Refactoring suggestion: The initial and final
            # values ​​of '_now' must be attributes of the operation
            self._now = self._get_initial_backtesting_now()
            self._final_backtesting_now = self._get_final_backtesting_now()

    def _get_ready_to_repeat(self):
        self._consolidate_log()

        if self.op.mode == MODE.BackTesting:
            self.op.print_report()
            self._now += self._step

            if self._now > self._final_backtesting_now:
                self.op.update(status=STAT.NotRunning)

        else:
            if self.op.position.side != SIDE.Zeroed:
                time.sleep(self._step)

            else:
                next_close_time = self.op.last_open_time + (2 * self._step)
                _time = (
                    next_close_time - pendulum.now("UTC").int_timestamp
                ) + 3
                time.sleep(_time)

            self._now = pendulum.now("UTC").int_timestamp



"""