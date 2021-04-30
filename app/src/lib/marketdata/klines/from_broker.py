# pylint: disable=too-few-public-methods

"""Deals specifically with klines, delivering them formatted as pandas
dataframes, with some extra methods, such as market indicators. This
module also acts as a queue for requesting klines from the brokers, in
order to do not exceed the their APIs limits. Finally, it also deals
with saving and reading klines to/from the 'time_series_storage'.
"""

import time

import pandas as pd

from ....lib.utils.exceptions import BrokerError, StorageError
from ....lib.utils.schemas import Ticker
from ....lib.utils.tools.formatting import remove_last_kline_if_unclosed
from ....lib.utils.tools.time_handlers import (
    Now,
    cooldown_time,
    time_frame_to_seconds,
)
from ...brokers import Fabric
from .base import DF, Getter


class GetterFromBroker(Getter):
    """Aims to serve as a queue for requesting klines (OHLC) through
    brokers endpoints, spliting the requests, in order to respect broker
    established limits. If a request limit is close to being reached,
    will pause the queue, until cooldown time pass. Returns sanitized
    klines to the client, formatted as pandas DataFrame."""

    __slots__ = [
        "_broker",
        "_time_frame",
        "_request_step",
    ]

    def __init__(self, broker: str, ticker: Ticker, time_frame: str = str()):
        self._broker = Fabric(broker).real()
        self._time_frame = self._validate_tf(time_frame)
        super().__init__(broker, ticker, time_frame=self.time_frame)
        self._request_step = self.__request_step()

    def _validate_tf(self, time_frame: str) -> str:
        time_frames = self._broker.settings.time_frames
        error_msg = "time_frame should be in {}".format(time_frames)
        if time_frame:
            if time_frame not in time_frames:
                raise ValueError(error_msg)
            return time_frame

        time_frame = min(time_frames)
        return time_frame

    @property
    def time_frame(self) -> str:
        """time frame str <amount><scale_unit> e.g. '1m', '2h'"""
        return self._time_frame

    @time_frame.setter
    def time_frame(self, time_frame_to_set):
        self._time_frame = self._validate_tf(time_frame_to_set)

    def oldest_open_time(self) -> int:
        kline = self._broker.oldest_kline(self.ticker.symbol, self.time_frame)
        return kline.Open_time.item()

    def newest_open_time(self) -> int:
        return Now().utc_timestamp()

    def __request_step(self) -> int:
        records_per_request = self._broker.settings.records_per_request
        seconds_time_frame = time_frame_to_seconds(self.time_frame)
        return records_per_request * seconds_time_frame

    def _get_core(self, since: int, until: int) -> DF:
        klines = pd.DataFrame()
        for timestamp in range(since, until + 1, self._request_step):
            attempt = 0
            while True:
                try:
                    if self._broker.max_requests_limit_hit():
                        time.sleep(10)

                    attempt += 1
                    _klines = self._broker.get_klines(
                        ticker_symbol=self.ticker.symbol,
                        time_frame=self._time_frame,
                        since=timestamp,
                    )
                    klines = klines.append(_klines, ignore_index=True)
                    # if self.store_klines_round_by_round:
                    #    self.storage.append(_klines)
                    break

                except (BrokerError, StorageError) as error:
                    if not self.settings.infinite_request_attempts:
                        raise Exception from error

                    print("Fail, due the error: ", error)
                    time.sleep(cooldown_time(attempt))

        if self.settings.ignore_unclosed_kline:
            klines = remove_last_kline_if_unclosed(klines, self.time_frame)
        return klines
