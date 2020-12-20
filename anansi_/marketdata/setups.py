# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument

""" Coleção de Setups de várias funções importantes.
"""

from pydantic import BaseModel, validator
from typing import Sequence

possible_price_metrics = ["o", "h", "l", "c", "oh2", "olc3", "ohlc4"]


class SmaTripleCrossSetup(BaseModel):
    """ Setup of Cross Simple Triple Moving Average """

    price_metrics: str = "ohlc4"
    number_samples: Sequence[int] = (3, 20, 80)

    @validator("price_metrics")
    def prevent_unavaliable_price_metrics(cls, value):
        avaliable = bool(value in possible_price_metrics)
        if not avaliable:
            raise ValueError(
                "Price metrics should be in {}".format(possible_price_metrics)
            )
        return value

    @validator("number_samples")
    def prevent_inconsistencies(cls, value):
        non_positive_values = bool(False in [bool(x > 0) for x in value])

        ascending_order = bool((value[2] > value[1] and value[1] > value[0]))

        correct_length = bool(len(value) == 3)

        if non_positive_values:
            raise ValueError("Number samples must be positive integers.")

        if not ascending_order:
            raise ValueError("Should be in ascending order.")

        if not correct_length:
            raise ValueError("Expected 3 integer values, no more, no less.")
        return value


class BollingerBandsSetup(BaseModel):
    price_metrics:str = "ohlc4"
    number_samples:int = 20
    number_STDs:int = 2

class FollowBullsSetup:
    class Trend:
        sma_triple_cross = SmaTripleCrossSetup()
        
    class Volatility:
        bollinger_bands = BollingerBandsSetup()