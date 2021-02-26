# pylint: disable=E1136
import sys

import pandas as pd

from ...utils.databases.sql.schemas import (
    BaseModel,
    ClassifierPayLoad,
    DateTimeType,
    Market,
)
from ..klines import klines_getter

thismodule = sys.modules[__name__]


class DidiClassifier:
    class DidiInversion:
        index_of_slow: int = 0
        index_of_fast: int = 0

        def reset(self):
            self.index_of_slow = 0
            self.index_of_fast = 0

    def __init__(
        self,
        market: Market,
        setup: BaseModel,
        backtesting: bool = False,
        result_length: int = 1,
    ):
        self.setup = setup
        self.klines_getter = klines_getter(
            market=market,
            time_frame=setup.time_frame,
            backtesting=backtesting,
        )
        self.result = pd.DataFrame()
        self.data = pd.DataFrame()
        self.didi_inversion = self.DidiInversion()
        self.result_length = result_length
        self.extra_length = 10

    def number_of_samples(self):
        n_didi = max(self.setup.didi_index.number_samples)
        n_minimal = max(self.setup.bollinger_bands.number_samples, n_didi)
        return n_minimal + self.result_length + self.extra_length

    def get_data_until(self, desired_datetime: DateTimeType) -> None:
        self.data = self.klines_getter.get(
            until=desired_datetime, number_of_candles=self.number_of_samples()
        )

    def apply_indicators_pipeline(self):
        self.data.apply_indicator.trend.didi_index(setup=self.setup.didi_index)
        self.data.apply_indicator.volatility.bollinger_bands(
            setup=self.setup.bollinger_bands
        )

    def _didi_factor(self):
        _len = self.result_length + self.extra_length
        delta_inversion = abs(
            self.didi_inversion.index_of_fast
            - self.didi_inversion.index_of_slow
        )
        return (_len - delta_inversion) / _len

    def _didi_analysis(self, result: pd.core.frame.DataFrame, index: int):
        self.result.loc[index, "Didi_factor"] = 0.0

        previous_slow = result.iloc[0].Didi_slow
        slow = result.iloc[1].Didi_slow
        slow_inversion = bool(slow / previous_slow < 0)

        previous_fast = result.iloc[0].Didi_fast
        fast = result.iloc[1].Didi_fast
        fast_inversion = bool(fast / previous_fast < 0)

        if slow_inversion:
            self.didi_inversion.index_of_slow = index
        if fast_inversion:
            self.didi_inversion.index_of_fast = index

        didi_trend = 1 if slow < 0 < fast else -1 if fast < 0 < slow else 0
        if didi_trend != 0:
            self.result.loc[index, "Didi_factor"] = self._didi_factor()

        self.result.loc[index, "Didi_trend"] = didi_trend

    def _bollinger_analysis(self, result: pd.core.frame.DataFrame, index: int):
        previous_bb_upper = result.iloc[0].BB_upper
        current_bb_upper = result.iloc[1].BB_upper

        previous_bb_lower = result.iloc[0].BB_lower
        current_bb_lower = result.iloc[1].BB_lower

        total_opened_bands = bool(
            (current_bb_upper > previous_bb_upper)
            and (current_bb_lower < previous_bb_lower)
        )
        only_upper_opened = bool(
            (current_bb_upper > previous_bb_upper)
            and (current_bb_lower >= previous_bb_lower)
        )
        only_lower_opened = bool(
            (current_bb_upper <= previous_bb_upper)
            and (current_bb_lower < previous_bb_lower)
        )

        self.result.loc[index, "Bollinger"] = (
            1.0
            if total_opened_bands
            else self.setup.only_upper_opened_weight
            if only_upper_opened
            else self.setup.only_lower_opened_weight
            if only_lower_opened
            else 0  # Both bands are closed.
        )

    def evaluate_indicators_results(self):
        self.didi_inversion.reset()
        _len = self.result_length + self.extra_length
        self.result = pd.DataFrame()
        self.result = self.result.append(self.data[-_len:], ignore_index=True)

        for i in range(2, _len):
            result = self.result[i - 2 : i]
            self._didi_analysis(result, i)
            self._bollinger_analysis(result, i)
            self.result.loc[i, "Result"] = (
                self.result.iloc[i].Didi_trend * self.result.iloc[i].Bollinger
            )

    def get_restult_at(
        self, desired_datetime: DateTimeType
    ) -> pd.core.frame.DataFrame:

        result = pd.DataFrame()
        self.get_data_until(desired_datetime)
        self.apply_indicators_pipeline()
        self.evaluate_indicators_results()
        result = result.append(
            self.result[-self.result_length :], ignore_index=True
        )
        return result


def get_classifier(payload: ClassifierPayLoad):
    """Given a market, returns an instance of the named setup.classifier_name
    classifier.

    Args: operation (Operation): An instance of an Operation

    Returns: Union[DidiClassifier]: The classifier
    """

    return getattr(thismodule, payload.classifier.name)(
        market=payload.market,
        setup=payload.classifier.setup,
        backtesting=payload.backtesting,
        result_length=payload.result_length,
    )
