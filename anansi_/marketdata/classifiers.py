import sys
from .models import Market
from .setups import SmaTripleCrossSetup, FollowBullsSetup
from .klines import klines_getter
import pandas as pd
from typing import Union

thismodule = sys.modules[__name__]


def classifier(
    market: Market,
    setup: Union[
        FollowBullsSetup,
    ],
    time_frame: str,
):
    classifier_name = (setup.__class__.__name__).split("Setup")[0]
    return getattr(thismodule, classifier_name)(
        market, setup, time_frame
    )


def cross_triple_sma(
    setup: SmaTripleCrossSetup, data: pd.core.frame.DataFrame
) -> None:
    _setup = type("", (), {})()
    _setup.price_metrics = setup.price_metrics

    for n in setup.number_samples:
        _setup.number_samples = n
        data.apply_indicator.trend.simple_moving_average(_setup)


class FollowBulls:
    def __init__(
        self, market: Market, setup: FollowBullsSetup, time_frame: str
    ):
        self.backtesting = False
        self.result = pd.DataFrame()
        self.market = market
        self.setup = setup
        self.time_frame = time_frame
        self.number_samples = max(setup.Trend.sma_triple_cross.number_samples)

    def _indicators_pipeline(self):
        # Trend indicators
        cross_triple_sma(
            setup=self.setup.Trend.sma_triple_cross,
            data=self.data,
        )

        # Volatility indicators
        self.data.apply_indicator.volatility.bollinger_bands(
            setup=self.setup.Volatility.bollinger_bands
        )

    def _analysis_of_indicators(self):
        self.result = self.data

    def restult_at(self, timestamp: int) -> pd.core.frame.DataFrame:
        klines = klines_getter(self.market, self.time_frame, self.backtesting)

        self.data = klines.get(
            until=timestamp, number_of_candles=self.number_samples
        )
        self._indicators_pipeline()
        self._analysis_of_indicators()

        return self.result
