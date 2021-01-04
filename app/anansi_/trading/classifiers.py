import sys
from typing import Union

import pandas as pd

from ..marketdata.klines import klines_getter
from ..sql_app.schemas import (
    BaseModel,
    DateTimeType,
    DidiIndexSetup,
    Market,
    SmaTripleCross,
)
from ..tools.time_handlers import next_closed_candle, seconds_in

thismodule = sys.modules[__name__]


def cross_triple_sma(
    setup: SmaTripleCross, data: pd.core.frame.DataFrame
) -> None:
    _setup = type("", (), {})()
    _setup.price_metrics = setup.price_metrics

    for n in setup.number_samples:
        _setup.number_samples = n
        data.apply_indicator.trend.simple_moving_average(_setup)


class KlinesBasedClassifier:
    def __init__(
        self,
        market: Market,
        time_frame: str,
        setup: BaseModel,
        backtesting: bool,
    ):
        self.market = market
        self.time_frame = time_frame
        self.time_frame_total_seconds = seconds_in(time_frame)
        self.setup = setup
        self.backtesting = backtesting
        self.klines_getter = klines_getter(market, time_frame, backtesting)
        self.number_samples: int = None
        self.data = pd.DataFrame()
        self.result = pd.DataFrame()
        self.time_until_next_closed_candle: int = None

    def get_data_until(self, desired_datetime: DateTimeType) -> None:
        self.data = self.klines_getter.get(
            until=desired_datetime, number_of_candles=self.number_samples
        )

    def initial_backtesting_now(self) -> int:
        oldest_open_time = self.klines_getter.oldest_open_time()
        step = self.number_samples * self.time_frame_total_seconds
        return oldest_open_time + step

    def final_backtesting_now(self) -> int:
        return self.klines_getter.newest_open_time()

    def restult_at(self, **kwargs):
        raise NotImplementedError


class DidiIndex(KlinesBasedClassifier):
    def __init__(
        self,
        market: Market,
        time_frame: str,
        setup: DidiIndexSetup = DidiIndexSetup(),
        backtesting: bool = False,
    ):
        super().__init__(market, time_frame, setup, backtesting)
        self.number_samples = max(setup.sma_triple_cross.number_samples)

    def _trend_analysis(self):
        small_sma, middle_sma, large_sma = (
            getattr(self.data, "SMA_{}".format(n)).tail(1).item()
            for n in self.setup.sma_triple_cross.number_samples
        )

        didi_fast_sma = small_sma / middle_sma - 1
        didi_slow_sma = large_sma / middle_sma - 1

        didi_result = (
            1
            if didi_slow_sma < 0 < didi_fast_sma
            else -1
            if didi_fast_sma < 0 < didi_slow_sma
            else 0
        )
        self.result["Trend_result"] = didi_result
        self.result["Didi_fast"] = didi_fast_sma
        self.result["Didi_slow"] = didi_slow_sma
        self.result["Didi_middle"] = 0.0

    def _volatility_analysis(self):
        previous_BB_upper = self.data[-2:-1].BB_upper.item()
        current_BB_upper = self.data[-1:].BB_upper.item()

        previous_BB_lower = self.data[-2:-1].BB_lower.item()
        current_BB_lower = self.data[-1:].BB_lower.item()

        total_opened_bands = bool(
            (current_BB_upper > previous_BB_upper)
            and (current_BB_lower < previous_BB_lower)
        )

        total_closed_bands = bool(
            (current_BB_upper <= previous_BB_upper)
            and (current_BB_lower >= previous_BB_lower)
        )

        bollinger_result = (
            1.0
            if total_opened_bands
            else 0.0
            if total_closed_bands
            else self.setup.weight_case_partial_opened
        )
        self.result["Bollinger_result"] = bollinger_result

    def _apply_indicators_pipeline(self):
        cross_triple_sma(
            setup=self.setup.sma_triple_cross,
            data=self.data,
        )
        self.data.apply_indicator.volatility.bollinger_bands(
            setup=self.setup.bollinger_bands
        )

    def _evaluate_indicators_values(self):
        self.result = pd.DataFrame()
        self.result = self.result.append(self.data[-1:], ignore_index=True)

        self._trend_analysis()
        self._volatility_analysis()

        leverage = (
            self.result.Trend_result.item()
            * self.result.Bollinger_result.item()
        )
        side = (
            "Long"
            if leverage > 0.3
            else "Short"
            if leverage < -0.3
            else "Zeroed"
        )
        self.result["Side"] = side
        self.result["Leverage"] = leverage

    def restult_at(
        self, desired_datetime: DateTimeType
    ) -> pd.core.frame.DataFrame:

        self.get_data_until(desired_datetime)
        self._apply_indicators_pipeline()
        self._evaluate_indicators_values()

        current_opentime = self.result.Open_time.tail(1).item()

        self.time_until_next_closed_candle = next_closed_candle(
            self.time_frame, current_opentime
        )

        return self.result


def get_classifier(
    classifier_name, market: Market, time_frame: str, **setup: BaseModel
) -> Union[DidiIndex,]:
    return getattr(thismodule, classifier_name)(market, time_frame, **setup)
