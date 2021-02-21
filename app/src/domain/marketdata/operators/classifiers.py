# pylint: disable=E1136
import sys

import pandas as pd

from ....repositories.sql_app.schemas import (
    BaseModel,
    ClassifierPayLoad,
    DateTimeType,
    Market,
)
from ..klines import klines_getter

thismodule = sys.modules[__name__]


class DidiClassifier:
    class DidiInversion:
        index_of_slow:int = 0
        index_of_fast:int = 0

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
        return (
            max(
                max(self.setup.didi_index.number_samples),
                self.setup.bollinger_bands.number_samples,
            )
        ) + self.result_length + self.extra_length

    def get_data_until(self, desired_datetime: DateTimeType) -> None:
        self.data = self.klines_getter.get(
            until=desired_datetime, number_of_candles=self.number_of_samples()
        )

    def apply_indicators_pipeline(self):
        self.data.apply_indicator.trend.didi_index(setup=self.setup.didi_index)
        self.data.apply_indicator.volatility.bollinger_bands(
            setup=self.setup.bollinger_bands
        )

    def _bollinger_analysis(self, result, index:int):
        previous_bb_upper = result.iloc[index].BB_upper
        current_bb_upper = result.iloc[index + 1].BB_upper

        previous_bb_lower = result.iloc[index].BB_lower
        current_bb_lower = result.iloc[index + 1].BB_lower

        total_opened_bands = bool(
            (current_bb_upper > previous_bb_upper)
            and (current_bb_lower < previous_bb_lower)
        )
        total_closed_bands = bool(
            (current_bb_upper <= previous_bb_upper)
            and (current_bb_lower >= previous_bb_lower)
        )
        self.result.loc[index + 1, "Bollinger"] = (
            1.0
            if total_opened_bands
            else 0.0
            if total_closed_bands
            else self.setup.partial_opened_bands_weight
        )

    def _didi_analysis(self, result, index:int):
        previous_slow = result.iloc[index].Didi_slow
        slow = result.iloc[index + 1].Didi_slow
        slow_inversion = bool(slow/previous_slow < 0)

        previous_fast = result.iloc[index].Didi_fast
        fast = result.iloc[index + 1].Didi_fast
        fast_inversion = bool(fast/previous_fast < 0)

        if slow_inversion:
            self.didi_inversion.index_of_slow = index + 1
        if fast_inversion:
            self.didi_inversion.index_of_fast = index + 1

        #Aqui deve fechar a análise de tendência, a partir da idéia de "alerta/confirmação"

        self.result.loc[index + 1, "Didi_index"] = (1 if slow < 0 < fast else -1 if fast < 0 < slow else 0)

    def evaluate_indicators_results(self):
        self.didi_inversion.reset()
        _len = self.result_length + self.extra_length
        self.result = pd.DataFrame()
        self.result = self.result.append(self.data[-_len:], ignore_index=True)

        for i in range(_len - 1):
            result = self.result[i:i+1]
            self._bollinger_analysis(result, i)
            self._didi_analysis(result, i)

    def get_restult_at(
        self, desired_datetime: DateTimeType
    ) -> pd.core.frame.DataFrame:

        self.get_data_until(desired_datetime)
        self.apply_indicators_pipeline()
        self.evaluate_indicators_results()
        return self.result[-self.result_length:]


def get_classifier(payload: ClassifierPayLoad):
    """Given a market, returns an instance of the named setup.classifier_name
    classifier.

    Args: operation (Operation): An instance of an Operation

    Returns: Union[DidiClassifier]: The classifier
    """

    return getattr(thismodule, payload.name)(
        market=payload.market,
        setup=payload.setup,
        backtesting=payload.backtesting,
        result_length=payload.result_length,
    )
