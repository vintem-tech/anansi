# pylint: disable=E1136
# pylint: disable=no-name-in-module
# pylint: disable=too-few-public-methods

import pandas as pd
from pydantic import BaseModel
from src.lib.marketdata.klines.operators.indicators.bollinger_bands import (
    Setup as BollingerBandsSetup,
)
from src.lib.marketdata.klines.operators.indicators.didi_index import (
    Setup as DidiIndexSetup,
)


class Setup(BaseModel):
    """Setup of DidiClassifier operator, which uses didi index and
    bollinger bands indicators to generate a classification score"""

    time_frame: str = "6h"
    didi_index = DidiIndexSetup()
    bollinger_bands = BollingerBandsSetup()
    # The values below must be in range(0.0, 1.0) | 'bb' = 'Bollinger bands'
    weight_if_only_upper_bb_opened: float = 0.7
    weight_if_only_bottom_bb_opened: float = 0.4


class MovingAverageInversionScore(BaseModel):
    index_of_slow: int = 0
    index_of_fast: int = 0
    number_of_observation_periods: int

    def reset_indexes(self):
        self.index_of_slow = 0
        self.index_of_fast = 0

    def calculate(self) -> float:
        """'delta_inversion' means the difference between the indexes
        (at the time of signal reversion) of each moving average. The
        lower 'delta_inversion', the higher score ( 0 <= score <=1 ).
        """

        window_len = self.number_of_observation_periods
        delta_inversion = abs(self.index_of_fast - self.index_of_slow)
        if delta_inversion > window_len:
            return 0.0
        return (window_len - delta_inversion) / window_len


class DidiClassifier:

    __slots__ = [
        "_klines",
        "setup",
        "_len_rolling_window",
        "_ma_inversion_score",
    ]

    def __init__(self, klines):
        self._klines = klines
        self.setup = None
        self._len_rolling_window = 20
        self._ma_inversion_score = MovingAverageInversionScore(
            number_of_observation_periods=self._len_rolling_window
        )

    def _minimum_number_samples(self):
        n_didi = max(self.setup.didi_index.number_samples)
        n_minimum = max(self.setup.bollinger_bands.number_samples, n_didi)
        return n_minimum + self._len_rolling_window

    def _apply_indicators_pipeline(self):
        self._klines.indicator.didi_index.apply(setup=self.setup.didi_index)
        self._klines.indicator.bollinger_bands.apply(
            setup=self.setup.bollinger_bands
        )

    def _didi_analysis(self, result: pd.core.frame.DataFrame, index: int):
        previous_slow = float(result.iloc[0].Didi_slow.item())
        slow = float(result.iloc[1].Didi_slow.item())
        slow_inversion = (slow / previous_slow) < 0

        previous_fast = float(result.iloc[0].Didi_fast.item())
        fast = float(result.iloc[1].Didi_fast.item())
        fast_inversion = (fast / previous_fast) < 0

        if slow_inversion:
            self._ma_inversion_score.index_of_slow = index
        if fast_inversion:
            self._ma_inversion_score.index_of_fast = index

        didi_trend = 1 if slow < 0 < fast else -1 if fast < 0 < slow else 0

        self._klines.loc[
            index, "Didi_score"
        ] = self._ma_inversion_score.calculate()

        self._klines.loc[index, "Didi_trend"] = didi_trend

    def _bollinger_analysis(self, result: pd.core.frame.DataFrame, index: int):
        self._klines.loc[index, "Bollinger"] = 0

        previous_bb_upper = result.iloc[0].BB_upper
        current_bb_upper = result.iloc[1].BB_upper

        previous_bb_bottom = result.iloc[0].BB_bottom
        current_bb_bottom = result.iloc[1].BB_bottom

        # total_opened_bands
        if (current_bb_upper > previous_bb_upper) and (
            current_bb_bottom < previous_bb_bottom
        ):
            self._klines.loc[index, "Bollinger"] = 1
            return

        # only_upper_bb_opened
        if (current_bb_upper > previous_bb_upper) and (
            current_bb_bottom >= previous_bb_bottom
        ):
            self._klines.loc[
                index, "Bollinger"
            ] = self.setup.weight_if_only_upper_bb_opened
            return

        # only_bottom_bb_opened
        if (current_bb_upper <= previous_bb_upper) and (
            current_bb_bottom < previous_bb_bottom
        ):
            self._klines.loc[
                index, "Bollinger"
            ] = self.setup.weight_if_only_bottom_bb_opened
            return

    def _evaluate_indicators_results(self):
        self._ma_inversion_score.reset_indexes()

        for i in range(2, len(self._klines) + 1):
            desired_index = i - 1
            two_rows_rolling_window = self._klines[i - 2 : i]

            self._didi_analysis(
                result=two_rows_rolling_window, index=desired_index
            )
            self._bollinger_analysis(
                result=two_rows_rolling_window, index=desired_index
            )

            result = self._klines.iloc[desired_index]

            self._klines.loc[desired_index, "Score"] = (
                result.Didi_trend * result.Bollinger * result.Didi_score
            )

    def apply(self, setup: Setup = Setup()):
        self.setup = setup
        n_samples_min = self._minimum_number_samples()

        if len(self._klines) < n_samples_min:
            raise IndexError(
                "Klines must have at least {} rows.".format(n_samples_min)
            )

        self._apply_indicators_pipeline()
        self._evaluate_indicators_results()
