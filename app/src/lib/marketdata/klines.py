# pylint: disable=too-few-public-methods

"""Deals specifically with klines, delivering them formatted as pandas
dataframes, with some extra methods, such as market indicators. This
module also acts as a queue for requesting klines from the brokers, in
order to do not exceed the their APIs limits. Finally, it also deals
with saving and reading klines to/from the 'time_series_storage'.
"""

import time

import pandas as pd
import pendulum

from ..brokers.engines import get_broker
from ..tools.time_handlers import (
    ParseDateTime,
    cooldown_time,
    datetime_as_integer_timestamp,
    time_frame_to_seconds,
)
from ..utils.databases.sql.schemas import DateTimeType, Market
from ..utils.databases.time_series_storage.models import StorageKlines
from ..utils.exceptions import BrokerError, KlinesError, StorageError
from .operators import indicators


@pd.api.extensions.register_dataframe_accessor("apply_indicator")
class ApplyIndicator:
    """Klines based market indicators, grouped by common scope."""

    def __init__(self, klines):
        self._klines = klines
        self.trend = indicators.Trend(self._klines)
        self.momentum = indicators.Momentum(self._klines)
        self.volatility = indicators.Volatility(self._klines)
        self.volume = indicators.Volume(self._klines)


def remove_last_kline_if_unclosed(
    klines: pd.DataFrame, time_frame: str
) -> pd.DataFrame:
    """If the last candle are not yet closed, it'll be elimated.

    Args:
        klines (pd.DataFrame): Candlesticks of the desired period Dataframe.

    Returns:
        pd.DataFrame: Adjusted Dataframe.
    """

    last_open_time = klines[-1:].Open_time.item()
    delta_time = (pendulum.now(tz="UTC")).int_timestamp - last_open_time
    unclosed = bool(delta_time < time_frame_to_seconds(time_frame))

    if unclosed:
        return klines[:-1]
    return klines


class KlinesFrom:
    """Parent class of FromBroker and Fromstorage"""

    __slots__ = [
        "market",
        "time_frame",
        "oldest_open_time",
        "storage",
        "return_as_human_readable",
        "ignore_unclosed_kline",
    ]

    def __init__(self, market: Market, time_frame: str = str()):
        self.market = market
        self.time_frame = time_frame
        self.storage = StorageKlines(
            table="{}_{}".format(
                market.broker_name.lower(),
                market.ticker_symbol.lower(),
            ),
            time_frame=time_frame,
        )
        self.oldest_open_time = self._oldest_open_time()
        self.return_as_human_readable = True
        self.ignore_unclosed_kline = True

    def _oldest_open_time(self) -> int:
        raise NotImplementedError

    def newest_open_time(self) -> int:
        """The newest avaliable open time (integer timestamp)"""
        raise NotImplementedError

    def _get_core(self, since: int, until: int) -> pd.core.frame.DataFrame:
        raise NotImplementedError

    def _timestamp_delta(self, number_samples: int) -> int:
        return int(
            time_frame_to_seconds(self.time_frame) * (number_samples - 1)
        )

    def _until(self, since: int, number_samples: int) -> int:
        until = since + self._timestamp_delta(number_samples)
        return int(
            until
            if until < self.newest_open_time()
            else self.newest_open_time()
        )

    def _since(self, until: int, number_samples: int) -> int:
        since = until - self._timestamp_delta(number_samples)
        return int(
            since if since > self.oldest_open_time else self.oldest_open_time
        )

    def _sanitize_get_input(self, **kwargs) -> tuple:
        since = kwargs.get("since")
        until = kwargs.get("until")
        number_samples: int = kwargs.get("number_samples")

        if since:
            _since = datetime_as_integer_timestamp(since)
            since = (
                _since
                if _since > self.oldest_open_time
                else self.oldest_open_time
            )
        if until:
            _until = datetime_as_integer_timestamp(until)
            until = (
                _until
                if _until < self.newest_open_time()
                else self.newest_open_time()
            )

        if since and until:  # This cover the scenario "start and stop and n"
            time_range = since, until
            if since > until:
                time_range = until, since

        elif number_samples and since and not until:
            time_range = since, self._until(since, number_samples)

        elif number_samples and until and not since:
            time_range = self._since(until, number_samples), until

        else:
            raise ValueError(
                """At least 2 of 3 arguments must be passed:
                'since=', 'until=', 'number_samples='"""
            )
        return (*(int(timestamp) for timestamp in time_range),)

    def get(self, **kwargs) -> pd.core.frame.DataFrame:
        """Solves the request, if that contains at least 2 of these 3
        arguments: "since", "until", "number_samples".

        Returns:
            pd.core.frame.DataFrame: Requested klines range."""

        since, until = self._sanitize_get_input(**kwargs)
        _klines = self._get_core(since, until)

        klines = _klines[_klines.Open_time <= until]

        if self.return_as_human_readable:
            klines.apply_datetime_conversion.from_timestamp_to_human_readable(
                target_columns=["Open_time"]
            )
        return klines

    def oldest(self, number_samples=1) -> pd.core.frame.DataFrame:
        """Oldest <number_samples> klines avaliable.

        Args:
            number_samples (int, optional): Desired number of samples
            (candles). Defaults to 1.

        Returns:
            pd.core.frame.DataFrame: klines, dataframe with extra methods.
        """
        klines = self.get(
            number_samples=number_samples, since=self.oldest_open_time
        )
        _len = min(number_samples, len(klines))
        return klines[:_len]

    def newest(self, number_samples=1) -> pd.core.frame.DataFrame:
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


class FromBroker(KlinesFrom):
    """Aims to serve as a queue for requesting klines (OHLC) through
    brokers endpoints, spliting the requests, in order to respect broker
    established limits. If a request limit is close to being reached,
    will pause the queue, until cooldown time pass. Returns sanitized
    klines to the client, formatted as pandas DataFrame."""

    __slots__ = [
        "_broker",
        "minimum_time_frame",
        "_time_frame",
        "store_klines_round_by_round",
        "infinite_attempts",
        "_request_step",
    ]

    def __init__(self, market: Market, time_frame: str = str()):
        self._broker = get_broker(market)
        self.minimum_time_frame = self._broker.settings.possible_time_frames[0]
        self._time_frame = self._validate_tf(time_frame)
        super().__init__(market, self.time_frame)
        self.store_klines_round_by_round: bool = False
        self.infinite_attempts: bool = True
        self._request_step = self.__request_step()

    def _validate_tf(self, timeframe: str):
        tf_list = self._broker.settings.possible_time_frames
        if timeframe:
            if timeframe not in tf_list:
                raise ValueError("Time frame must be in {}".format(tf_list))
        else:
            timeframe = self.minimum_time_frame
        return timeframe

    @property
    def time_frame(self) -> str:
        """time frame str <amount><scale_unit> e.g. '1m', '2h'"""
        return self._time_frame

    @time_frame.setter
    def time_frame(self, time_frame_to_set):
        self._time_frame = self._validate_tf(time_frame_to_set)

    def _oldest_open_time(self) -> int:
        return self._broker.oldest_kline(self.time_frame).Open_time.item()

    def newest_open_time(self) -> int:
        return (pendulum.now(tz="UTC")).int_timestamp

    def __request_step(self) -> int:
        return (
            self._broker.settings.records_per_request
            * time_frame_to_seconds(self.time_frame)
        )

    def _get_core(self, since: int, until: int) -> pd.core.frame.DataFrame:
        klines = pd.DataFrame()
        for timestamp in range(since, until + 1, self._request_step):
            attempt = 0
            while True:
                try:
                    if self._broker.max_requests_limit_hit():
                        time.sleep(10)
                    else:
                        attempt += 1
                        _klines = self._broker.get_klines(
                            time_frame=self._time_frame,
                            since=timestamp,
                        )
                        klines = klines.append(_klines, ignore_index=True)
                        if self.store_klines_round_by_round:
                            self.storage.append(_klines)
                        break

                except (BrokerError, StorageError) as err:
                    if self.infinite_attempts:
                        print("Fail, due the error: ", err)
                        time.sleep(cooldown_time(attempt))
                    else:
                        raise Exception.with_traceback(err) from err

        if self.ignore_unclosed_kline:
            klines = remove_last_kline_if_unclosed(klines, self.time_frame)
        return klines


class FromStorage(KlinesFrom):
    """Entrypoint for requests to the stored klines"""

    def _oldest_open_time(self) -> int:
        return self.storage.oldest_open_time()

    def newest_open_time(self) -> int:
        return self.storage.newest_open_time()

    def _get_core(self, since: int, until: int) -> pd.core.frame.DataFrame:
        try:
            return self.storage.get_by_time_range(since, until)
        except StorageError as err:
            raise Exception.with_traceback(err) from StorageError


class ToStorage:
    """Entrypoint to append klines to StorageKlines"""

    __slots__ = ["klines"]

    def __init__(self, market: Market):
        self.klines = FromBroker(market)
        self.klines.store_klines_round_by_round = True

    def create_backtesting(self, **kwargs) -> pd.core.frame.DataFrame:
        """Any (valid!) timeframe klines, on interval [since, until].

        Args:
            since (DateTimeType): Start desired datetime
            until (DateTimeType): End desired datetime

        Returns:
            pd.core.frame.DataFrame: Raw timestamp formatted OHLCV
            (klines) dataframe
        """

        self.klines.time_frame = kwargs.get(
            "time_frame", self.klines.minimum_time_frame
        )
        return self.klines.get(
            since=kwargs.get("since", self.klines.oldest_open_time),
            until=kwargs.get("until", self.klines.newest_open_time()),
        )


class PriceFromStorage:
    """Useful for backtesting scenarios, in order to be able to emulate
    the instant price at any past time; to do so, uses the finer-grained
    klines. The mass of requested klines is extensive (approximately 16h
    backwards and 16h forwards) since, as 'StorageKlines' takes care of
    the interpolation, it is prudent to predict long missing masses of
    data."""

    def __init__(self, market: Market, price_metrics="ohlc4"):
        self.klines_getter = FromStorage(market, "1m")
        self.price_metrics = price_metrics

    def _valid_timestamp(self, timestamp: int) -> bool:
        return bool(timestamp <= self.klines_getter.newest_open_time())

    def get_price_at(self, desired_datetime: DateTimeType) -> float:
        """A 'fake' past ticker price"""

        desired_datetime = datetime_as_integer_timestamp(desired_datetime)

        if self._valid_timestamp(desired_datetime):
            _until = desired_datetime + 60000

            try:
                klines = self.klines_getter.get(
                    since=desired_datetime - 60000,
                    until=(
                        _until
                        if self._valid_timestamp(_until)
                        else desired_datetime
                    ),
                )
                klines.apply_indicator.trend.price_from_kline(
                    self.price_metrics
                )
                klines.apply_datetime_conversion.from_human_readable_to_timestamp(
                    target_columns=["Open_time"]
                )
                desired_kline = klines.loc[  #!TODO: Revisar isto
                    klines.Open_time == desired_datetime
                ]
                price = getattr(
                    desired_kline, "Price_{}".format(self.price_metrics)
                )
                return price.item()

            except KlinesError as err:
                raise Exception.with_traceback(err) from KlinesError

        else:
            raise ValueError(
                "desired_datetime > newest stored datetime ({})!".format(
                    ParseDateTime(
                        self.klines_getter.newest_open_time()
                    ).from_timestamp_to_human_readable()
                )
            )


def klines_getter(market: Market, time_frame: str = str(), backtesting=False):
    """Instantiates a 'KlinesFrom' object, in order to handler klines.

    Args:
        market (Market): Broker name and assets information

        time_frame (str, optional): <amount><scale_unit> e.g. '1m',
        '2h'. Defaults to '' (empty string).

        backtesting (bool, optional): If True, get interpolated klines
        from time series storage. Defaults to False.

    Returns:
        [KlinesFrom]: 'FromBroker' or 'FromStorage' klines getter
    """
    if backtesting:
        return FromStorage(market, time_frame)
    return FromBroker(market, time_frame)
