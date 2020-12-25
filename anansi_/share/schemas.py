# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument
# pylint: disable=too-few-public-methods

"""Shared pydantic model classes.

TimeFormat below could be:
  - integer or string timestamp, measured in seconds or
  - human readable datetime, 'YYYY-MM-DD HH:mm:ss' formated;
    e.g. '2017-11-08 10:00:00'.

  Both should be passed converted or originally measured on UTC timezone; this
  software does not perform this kind of conversion.
"""

from typing import Union
from pydantic import BaseModel

TimeFormat = Union[str, int]


class Market(BaseModel):
    """ Market attributes """

    broker_name: str
    quote_symbol: str
    base_symbol: str

    @property
    def ticker_symbol(self):
        """Returns the symbol of a market ticket

        Returns:
            str: quote_symbol + base_symbol
        """
        return self.quote_symbol + self.base_symbol


class TimeRange(BaseModel):
    """collect the start and end of a time range"""

    start_time: TimeFormat
    end_time: TimeFormat
