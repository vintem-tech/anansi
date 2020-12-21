import sys
from .models import BaseModel, Market, SmaTripleCross
from .klines import klines_getter
import pandas as pd
from typing import Union

# thismodule = sys.modules[__name__]

# def classifier(
#    market: Market,
#    setup: Union[
#        FollowBullsSetup,
#    ],
#    time_frame: str,
# ):
#    classifier_name = (setup.__class__.__name__).split("Setup")[0]
#    return getattr(thismodule, classifier_name)(
#        market, setup, time_frame
#    )


def cross_triple_sma(
    setup: SmaTripleCross, data: pd.core.frame.DataFrame
) -> None:
    _setup = type("", (), {})()
    _setup.price_metrics = setup.price_metrics

    for n in setup.number_samples:
        _setup.number_samples = n
        data.apply_indicator.trend.simple_moving_average(_setup)


class DidiIndexAlpha:
    def __init__(self, market: Market, setup: BaseModel, time_frame: str):
        self.backtesting = False
        self.result = pd.DataFrame()
        self.market = market
        self.setup = setup
        self.time_frame = time_frame
        self.number_samples = max(setup.simple_moving_average.number_samples)

    def _trend_analysis(self):
        small_sma, middle_sma, large_sma = (
            getattr(self.data, "SMA_{}".format(n)).tail(1).item()
            for n in self.setup.simple_moving_average.number_samples
        )

        didi_fast_sma = small_sma / middle_sma - 1
        didi_slow_sma = large_sma / middle_sma - 1

        didi_result = (
            1
            if (didi_fast_sma > 0 and didi_slow_sma < 0)
            else -1
            if (
                didi_fast_sma < 0
                and didi_slow_sma > 0
                and self.setup.allow_naked_sells
            )
            else 0
        )
        self.result["Trend_result"] = didi_result
        self.result["Didi_fast"] = didi_fast_sma
        self.result["Did_slow"] = didi_slow_sma

    def _volatility_analysis(self):
        previous_BB_upper = self.data[-2:-1].BB_upper.item()
        current_BB_upper = self.data[-1:].BB_upper.item()

        previous_BB_lower = self.data[-2:-1].BB_lower.item()
        current_BB_lower = self.data[-1:].BB_lower.item()

        total_opened_bands = bool(
            (current_BB_upper > previous_BB_upper)
            and (current_BB_lower < previous_BB_lower)
        )
        partial_opened_bands = bool(
            (
                (current_BB_upper > previous_BB_upper)
                and (current_BB_lower >= previous_BB_lower)
            )
            or (
                (current_BB_upper <= previous_BB_upper)
                and (current_BB_lower < previous_BB_lower)
            )
        )
        bollinger_result = (
            1 if total_opened_bands else 0.5 if partial_opened_bands else 0
        )
        self.result["Bollinger_result"] = bollinger_result

    def _indicators_pipeline(self):
        cross_triple_sma(
            setup=self.setup.simple_moving_average,
            data=self.data,
        )
        self.data.apply_indicator.volatility.bollinger_bands(
            setup=self.setup.bollinger_bands
        )

    def _analysis_of_indicators(self):
        self.result = pd.DataFrame()
        self.result = self.result.append(self.data[-1:], ignore_index=True)

        self._trend_analysis()
        self._volatility_analysis()

        leverage = (
            self.result.Trend_result.item()
            * self.result.Bollinger_result.item()
        )
        suggest_side = (
            "Long"
            if leverage > 0.3
            else "Short"
            if leverage < -0.3
            else "Zeroed"
        )
        self.result["Suggest_side"] = suggest_side
        self.result["Leverage"] = leverage

    def restult_at(
        self, desired_datetime: Union[str, int]
    ) -> pd.core.frame.DataFrame:
        klines = klines_getter(self.market, self.time_frame, self.backtesting)

        self.data = klines.get(
            until=desired_datetime, number_of_candles=self.number_samples
        )
        self._indicators_pipeline()
        self._analysis_of_indicators()

        return self.result
