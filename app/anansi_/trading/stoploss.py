# pylint: disable=E1136

import sys
from typing import Union

from ..sql_app.schemas import Treshold, Trigger
from ..tools.serializers import Deserialize

thismodule = sys.modules[__name__]


class StopTrailing3T:
    def __init__(self, operation):
        self.operation = operation
        self.setup = Deserialize(name="setup").from_json(operation.setup)
        self.klines_getter = klines_getter(
            market=market,
            time_frame=setup.time_frame,
            backtesting=backtesting,
        )
        self.data = pd.DataFrame()
        self.result = pd.DataFrame()

    def verify(self):
        pass

    def sleep_time(self):
        return 60

    def time_frame_total_seconds(self):
        return 60


def get_stop(
    operation,
) -> Union[StopTrailing3T,]:
    """Instantiates a stoploss handler"""

    _setup = Deserialize(name="setup").from_json(operation.setup)
    stoploss_name = _setup.stoploss_name
    return getattr(thismodule, stoploss_name)(operation)
