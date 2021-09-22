"""Basic classes and functions for processing klines"""

# pylint: disable=no-name-in-module
# pylint: disable=too-few-public-methods
# pylint: disable=too-many-return-statements

import pandas as pd
from pydantic import BaseModel

from ....utils.databases.time_series_storage.models import StorageKlines
from ....utils.exceptions import TimeFormatError
from ....utils.schemas.generics import Ticker
from ....utils.tools.time_handlers import int_timestamp, time_frame_to_seconds
from .operators.classifiers import didi_v1 as didi
from .operators.indicators import (
    bollinger_bands,
    didi_index,
    price,
    simple_moving_average as sma,
)

DF = pd.core.frame.DataFrame
pd.options.mode.chained_assignment = None


class GetterSettings(BaseModel):
    return_as_human_readable = True
    ignore_unclosed_kline = True
    infinite_request_attempts = True


class GetInputSanitizer(BaseModel):
    sec_time_frame: int
    min_timestamp: int
    max_timestamp: int

    def _timestamp_delta(self, number_samples: int) -> int:
        return int(self.sec_time_frame * (number_samples - 1))

    def _until(self, since: int, number_samples: int) -> int:
        until = since + self._timestamp_delta(number_samples)
        return min(until, self.max_timestamp)

    def _since(self, until: int, number_samples: int) -> int:
        since = until - self._timestamp_delta(number_samples)
        return max(since, self.min_timestamp)

    def sanitize(self, **kwargs) -> tuple:
        since = kwargs.get("since")
        until = kwargs.get("until")
        number_samples: int = kwargs.get("number_samples")

        if since:
            since = max(int_timestamp(since), self.min_timestamp)
            if not until and not number_samples:
                return since, self.max_timestamp

        if until:
            until = min(int_timestamp(until), self.max_timestamp)
            if not since and not number_samples:
                return self.min_timestamp, until

        # Also the scenario "since and until and number_samples"
        if since and until:
            if since > until:
                return until, since
            return since, until

        if number_samples and since and not until:
            return since, self._until(since, number_samples)

        if number_samples and until and not since:
            return self._since(until, number_samples), until

        # No inputs scenario
        return self.min_timestamp, self.max_timestamp


class Getter:
    """Methods and attributes common to the classes 'GetterFromBroker'
    (module 'from_broker') and 'GetterFromStorage' (module 'storage')
    """

    __slots__ = [
        "broker_name",
        "ticker",
        "time_frame",
        "settings",
        "storage",
        "sanitizer",
    ]

    def __init__(self, broker: str, ticker: Ticker, time_frame: str = str()):
        self.broker_name: broker
        self.ticker = ticker
        self.time_frame = time_frame
        self.settings = GetterSettings()
        self.storage = StorageKlines(
            table="{}_{}".format(broker.lower(), ticker.symbol.lower()),
            time_frame=self.time_frame,
        )
        self.sanitizer = GetInputSanitizer(
            sec_time_frame=time_frame_to_seconds(time_frame),
            min_timestamp=self.oldest_open_time(),
            max_timestamp=self.newest_open_time(),
        )

    def oldest_open_time(self) -> int:
        """The oldest avaliable open time (integer timestamp)"""
        raise NotImplementedError

    def newest_open_time(self) -> int:
        """The newest avaliable open time (integer timestamp)"""
        raise NotImplementedError

    def _get_core(self, since: int, until: int) -> DF:
        raise NotImplementedError

    def get(self, **kwargs) -> DF:
        """Solves the request, if that contains at least 2 of these 3
        arguments: "since", "until", "number_samples".

        Returns:
            pd.core.frame.DataFrame: Requested klines range."""

        since, until = self.sanitizer.sanitize(**kwargs)
        _klines = self._get_core(since, until)

        klines = _klines[_klines.Open_time <= until]
        if self.settings.return_as_human_readable:
            try:
                klines.parse_datetime.to_human_readable(
                    columns=["Open_time", "Close_time"]
                )
            except (KeyError, TimeFormatError):
                pass
        return klines

    def oldest(self, number_samples: int = 1) -> DF:
        """Oldest <number_samples> klines avaliable.

        Args:
            number_samples (int, optional): Desired number of samples
            (candles). Defaults to 1.

        Returns:
            pd.core.frame.DataFrame: klines, dataframe with extra methods.
        """
        klines = self.get(
            number_samples=number_samples, since=self.oldest_open_time()
        )
        _len = min(number_samples, len(klines))
        return klines[:_len]

    def newest(self, number_samples: int = 1) -> DF:
        """Newest <number_samples> klines avaliable.

        Args:
            number_samples (int, optional): Desired number of samples
            (candles). Defaults to 1.

        Returns:
            pd.core.frame.DataFrame: klines, dataframe with extra methods.
        """
        klines = self.get(
            number_samples=number_samples, until=self.newest_open_time()
        )
        _len = min(number_samples, len(klines))
        return klines[-_len:]


@pd.api.extensions.register_dataframe_accessor("indicator")
class Indicator:
    """Market indicators; obtained exclusively from klines (OHLCV)"""

    __slots__ = [
        "price",
        "simple_moving_average",
        "didi_index",
        "bollinger_bands",
    ]

    def __init__(self, klines: DF):
        self.price = price.PriceFromKline(klines)
        self.simple_moving_average = sma.SimpleMovingAverage(klines)
        self.didi_index = didi_index.DidiIndex(klines)
        self.bollinger_bands = bollinger_bands.BollingerBands(klines)


@pd.api.extensions.register_dataframe_accessor("classifier")
class Classifier:
    """Market classifiers; obtained exclusively from klines (OHLCV)"""

    __slots__ = [
        "didi",
    ]

    def __init__(self, klines: DF):
        self.didi = didi.DidiClassifier(klines)
