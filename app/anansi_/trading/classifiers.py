# pylint: disable=E1136

import sys
from typing import Union

import pandas as pd

from ..marketdata.klines import klines_getter
from ..sql_app.schemas import BaseModel, DateTimeType, Market
from ..tools.time_handlers import seconds_in, time_until_next_closed_candle

thismodule = sys.modules[__name__]


class DidiClassifier:
    def __init__(self, market: Market, setup: BaseModel, backtesting=False):
        self.setup = setup
        self.klines_getter = klines_getter(
            market=market,
            time_frame=setup.time_frame,
            backtesting=backtesting,
        )
        self.data = pd.DataFrame()
        self.result = pd.DataFrame()

    def number_of_samples(self):
        return max(
            max(self.setup.didi_index.number_samples),
            self.setup.bollinger_bands.number_samples,
        )

    def time_frame_total_seconds(self):
        return seconds_in(self.setup.time_frame)

    def time_until_next_closed_candle(self):
        return time_until_next_closed_candle(
            time_frame=self.setup.time_frame,
            current_open_time=self.result.Open_time.tail(1).item(),
        )

    def get_data_until(self, desired_datetime: DateTimeType) -> None:
        self.data = self.klines_getter.get(
            until=desired_datetime, number_of_candles=self.number_of_samples()
        )

    def initial_backtesting_now(self) -> int:
        oldest_open_time = self.klines_getter.oldest_open_time()
        step = self.number_of_samples() * self.time_frame_total_seconds()
        return oldest_open_time + step

    def final_backtesting_now(self) -> int:
        return self.klines_getter.newest_open_time()

    def _trend_analysis(self):
        slow = self.data.Didi_slow.tail(1).item()
        fast = self.data.Didi_fast.tail(1).item()

        didi_result = 1 if slow < 0 < fast else -1 if fast < 0 < slow else 0
        self.result["Trend_result"] = didi_result

    def _volatility_analysis(self):
        previous_bb_upper = self.data[-2:-1].BB_upper.item()
        current_bb_upper = self.data[-1:].BB_upper.item()

        previous_bb_lower = self.data[-2:-1].BB_lower.item()
        current_bb_lower = self.data[-1:].BB_lower.item()

        total_opened_bands = bool(
            (current_bb_upper > previous_bb_upper)
            and (current_bb_lower < previous_bb_lower)
        )
        total_closed_bands = bool(
            (current_bb_upper <= previous_bb_upper)
            and (current_bb_lower >= previous_bb_lower)
        )
        bollinger_weight = (
            1.0
            if total_opened_bands
            else 0.0
            if total_closed_bands
            else self.setup.partial_opened_bollinger_bands_weight
        )
        self.result["Bollinger_weight"] = bollinger_weight

    def _apply_indicators_pipeline(self):
        self.data.apply_indicator.trend.didi_index(setup=self.setup.didi_index)
        self.data.apply_indicator.volatility.bollinger_bands(
            setup=self.setup.bollinger_bands
        )

    def _evaluate_indicators_results(self):
        self.result = pd.DataFrame()
        self.result = self.result.append(self.data[-1:], ignore_index=True)

        self._trend_analysis()
        self._volatility_analysis()

        leverage = (
            self.result.Trend_result.item()
            * self.result.Bollinger_weight.item()
        )
        side = (
            "Long"
            if leverage > 0.3
            else "Short"
            if leverage < -0.3
            else "Zeroed"
        )
        self.result["Side"] = side
        self.result["Leverage"] = abs(leverage)

    def restult_at(
        self, desired_datetime: DateTimeType
    ) -> pd.core.frame.DataFrame:

        self.get_data_until(desired_datetime)
        self._apply_indicators_pipeline()
        self._evaluate_indicators_results()

        return self.result


def get_classifier(
    classifier_name: str, market: Market, setup: BaseModel, backtesting=False
) -> Union[DidiClassifier]:
    return getattr(thismodule, classifier_name)(market, setup, backtesting)
