# pylint: disable=no-name-in-module

from pydantic import BaseModel

from ...utils.schemas import Ticker #, TimeRange
from ...utils.tools.time_handlers import (datetime_as_integer_timestamp,
                                          time_frame_to_seconds)


class GetterSettings(BaseModel):
    return_as_human_readable = True
    ignore_unclosed_kline = True

class SanitizeGetInput:
    pass


class Getter:

    def __init__(self, broker_name:str, ticker: Ticker, time_frame: str = str()):
        self.broker_name: broker_name
        self.ticker = ticker
        self.time_frame = time_frame
        self.getter_settings = GetterSettings()
        self._oldest_open_time = self.oldest_open_time()
        self._newest_open_time = self.newest_open_time()

    def _timestamp_delta(self, number_samples: int) -> int:
        return int(
            time_frame_to_seconds(self.time_frame) * (number_samples - 1)
        )

    def _until(self, since: int, number_samples: int) -> int:
        until = since + self._timestamp_delta(number_samples)
        return min(until, self._newest_open_time)

    def _since(self, until: int, number_samples: int) -> int:
        since = until - self._timestamp_delta(number_samples)
        return max(since, self.oldest_open_time)

    def _sanitize_get_input(self, **kwargs) -> tuple:
        since = kwargs.get("since")
        until = kwargs.get("until")
        number_samples: int = kwargs.get("number_samples")

        if since:
            since_ = datetime_as_integer_timestamp(since)
            since = max(since_, self._oldest_open_time)

            if not until and not number_samples:
                return since, self._newest_open_time

        if until:
            until_ = datetime_as_integer_timestamp(until)
            until = min(until_, self._newest_open_time)

            if not since and not number_samples:
                return self._oldest_open_time, until

        if since and until:  # This cover the scenario "start and stop and n"
            if since > until:
                return until, since
            return since, until

        if number_samples and since and not until:
            return since, self._until(since, number_samples)

        if number_samples and until and not since:
            return self._since(until, number_samples), until

        return self._oldest_open_time, self._newest_open_time


    def oldest_open_time(self) -> int:
        """The oldest avaliable open time (integer timestamp)"""
        raise NotImplementedError

    def newest_open_time(self) -> int:
        """The newest avaliable open time (integer timestamp)"""
        raise NotImplementedError



@pd.api.extensions.register_dataframe_accessor("apply_indicator")
class ApplyIndicator:
    """Klines based market indicators, grouped by common scope."""

    def __init__(self, klines):
        self._klines = klines
        self.trend = indicators.Trend(self._klines)
        self.momentum = indicators.Momentum(self._klines)
        self.volatility = indicators.Volatility(self._klines)
        self.volume = indicators.Volume(self._klines)
