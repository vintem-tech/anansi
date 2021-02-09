# pylint: disable=no-name-in-module
# pylint: disable=E1136

from typing import Union #, Sequence, Optional, List
from pydantic import BaseModel #, validator

from ..sql_app.schemas import (
    BackTesting,
    DidiClassifierSetup,
    Market,
    OperationSetup,
    StopTrailing3T,
    Order,
)

class Messages:
    """A collection of formated commom messages that should be useful
    to monitoring trading routines."""

    @staticmethod
    def initial(the_id: Union[str, int], setup: BaseModel) -> str:

        return "Starting Anansi. Your operation id is {}\n\n{}".format(
            the_id, text_in_lines_from_dict(setup.as_dict())
        )

    @staticmethod
    def time_monitoring(now: int, step: int) -> str:
        """
        Return human readable formatted message about time (now and
        sleep/step time)
        """

        return """Time now (UTC) = {}\nSleeping {} s.""".format(
            ParseDateTime(now).from_timestamp_to_human_readable(), str(step)
        )
    
    @staticmethod
    def final(the_id: Union[str, int]) -> str:
        return "Op. {} finalized!".format(the_id)


back_testing = OperationSetup(
    debbug=True,
    backtesting = BackTesting(is_on=True),
    broadcasters=["PrintNotifier"],
    classifier_name="DidiClassifier",
    classifier_setup=DidiClassifierSetup(),
    stoploss_name="StopTrailing3T",
    stoploss_setup=StopTrailing3T(),
    market=Market(
        broker_name="Binance",
        quote_symbol="BTC",
        base_symbol="USDT",
        ticker_symbol="BTCUSDT",
    ),
    default_order = Order(
        notify=True,
        order_type="market",
    ),
    stop_is_on=True,
    allow_naked_sells=False,
)