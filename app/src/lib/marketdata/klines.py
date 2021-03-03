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
    sanitize_input_datetime,
    time_frame_to_seconds,
)
from ..utils.databases.sql.schemas import DateTimeType, Market
from ..utils.databases.time_series_storage.models import StorageKlines
from .operators import indicators

pd.options.mode.chained_assignment = None


@pd.api.extensions.register_dataframe_accessor("KlinesDateTime")
class KlinesDateTime:
    """Converts 'Open_time' and/or 'Close_time' columns items to/from
    timestamp/human readable."""

    def __init__(self, klines: pd.core.frame.DataFrame):
        self._klines = klines

    def from_human_readable_to_timestamp(self):
        """If human readable str, returns associated int timestamp."""
        self._klines.loc[:, "Open_time"] = self._klines.apply(
            lambda date_time: ParseDateTime(
                date_time["Open_time"]
            ).from_human_readable_to_timestamp(),
            axis=1,
        )

        if "Close_time" in self._klines:
            self._klines.loc[:, "Close_time"] = self._klines.apply(
                lambda date_time: ParseDateTime(
                    date_time["Close_time"]
                ).from_human_readable_to_timestamp(),
                axis=1,
            )

    def from_timestamp_to_human_readable(self):
        """If int timestamp, returns associated human readable str."""
        self._klines.loc[:, "Open_time"] = self._klines.apply(
            lambda date_time: ParseDateTime(
                date_time["Open_time"]
            ).from_timestamp_to_human_readable(),
            axis=1,
        )

        if "Close_time" in self._klines:
            self._klines.loc[:, "Close_time"] = self._klines.apply(
                lambda date_time: ParseDateTime(
                    date_time["Close_time"]
                ).from_timestamp_to_human_readable(),
                axis=1,
            )


@pd.api.extensions.register_dataframe_accessor("apply_indicator")
class ApplyIndicator:
    """Klines based market indicators, grouped by common scope."""

    def __init__(self, klines):
        self._klines = klines
        self.trend = indicators.Trend(self._klines)
        self.momentum = indicators.Momentum(self._klines)
        self.volatility = indicators.Volatility(self._klines)
        self.volume = indicators.Volume(self._klines)


class KlinesFrom:
    """Parent class of FromBroker and Fromstorage"""

    __slots__ = [
        "market",
        "time_frame",
        "oldest_open_time",
        "newest_open_time",
    ]

    def __init__(self, market: Market, time_frame: str):
        self.market = market
        self.time_frame = time_frame
        self.oldest_open_time: int = self._oldest_open_time()
        self.newest_open_time:int = self._newest_open_time()

    def _oldest_open_time(self) -> int:
        raise NotImplementedError

    def _newest_open_time(self) -> int:
        raise NotImplementedError

    def _get_core(self, since: int, until: int) -> pd.core.frame.DataFrame:
        raise NotImplementedError

    def _timestamp_delta(self, n: int) -> int:
        return int(time_frame_to_seconds(self.time_frame) * (n + 1))

    def _until(self, since: int, n: int) -> int:
        until = since + self._timestamp_delta(n)
        return (
            until if until < self.newest_open_time else self.newest_open_time
        )

    def _since(self, until: int, n: int) -> int:
        since = until - self._timestamp_delta(n)
        return (
            since if since > self.oldest_open_time else self.oldest_open_time
        )

    def _sanitize_get_input(self, **kwargs) -> tuple:
        since = kwargs.get("since")
        until = kwargs.get("until")
        number_samples: int = kwargs.get("number_samples")

        if since:
            since = sanitize_input_datetime(since)
            since = (
                since
                if since > self.oldest_open_time
                else self.oldest_open_time
            )
        if until:
            until = sanitize_input_datetime(until)
            until = (
                until
                if until < self.newest_open_time
                else self.newest_open_time
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
                "At least 2 of 3 arguments (since, until, number_samples) must be passed"
            )
        return time_range

    def get(self, human_readable=True, **kwargs) -> pd.core.frame.DataFrame:
        """Solves the request, if that contains at least 2 of these
        3 arguments: "since", "until", "number_samples".

        Returns:
            pd.core.frame.DataFrame: Requested klines range.
        """

        since, until = self._sanitize_get_input(**kwargs)
        klines = self._get_core(since, until)
        klines = klines[until >= klines.Open_time >= since]
        if human_readable:
            klines.KlinesDateTime.from_timestamp_to_human_readable()
        return klines

    def oldest(self, number_samples=1) -> pd.core.frame.DataFrame:
        klines = self.get(number_samples=number_samples, since=self.oldest_open_time)
        _len = min(number_samples, len(klines))
        return klines[:_len]

    def newest(self, number_samples=1) -> pd.core.frame.DataFrame:
        klines = self.get(number_samples=number_samples, until=self.newest_open_time)
        _len = min(number_samples, len(klines))
        return klines[-_len:]

class FromBroker(KlinesFrom):
    """Aims to serve as a queue for requesting klines (OHLC) through brokers
    endpoints, spliting the requests, in order to respect broker established
    limits.
    If a request limit is close to being reached, will pause the queue,
    until cooldown time pass.
    Returns sanitized klines to the client, formatted as pandas DataFrame.
    """

    __slots__ = [
        "_broker",
        "_time_frame",
        "_append_to_storage",
        "storage_name",
    ]

    def __init__(self, market: Market, time_frame: str = str()):
        self._broker = get_broker(market)
        super().__init__(market, time_frame)
        self._time_frame = self._validate_tf(time_frame)
        self._append_to_storage: bool = False
        self.storage_name: str = str()

    def _validate_tf(self, timeframe: str):
        tf_list = self._broker.settings.possible_time_frames
        if timeframe:
            if timeframe not in tf_list:
                raise ValueError("Time frame must be in {}".format(tf_list))
        else:
            timeframe = tf_list[0]
        return timeframe

    @property
    def time_frame(self):
        return self._time_frame

    @time_frame.setter
    def time_frame(self, time_frame_to_set):
        tf = self._validate_tf(time_frame_to_set)
        self._time_frame = tf

    def oldest_open_time(self) -> int:
        oldest_candle = self._broker.get_klines(
            ticker_symbol=self.market.ticker_symbol,
            time_frame=self._time_frame,
            since=1,
            number_samples=1,
        )
        return oldest_candle.Open_time.item()

    def newest_open_time(self) -> int:
        return (pendulum.now(tz="UTC")).int_timestamp

    def _request_step(self) -> int:
        n_per_req = self._broker.settings.records_per_request
        return n_per_req * time_frame_to_seconds(self.time_frame)

    def _get_core(self, since: int, until: int) -> pd.core.frame.DataFrame:

        klines = pd.DataFrame()
        for timestamp in range(since, until + 1, self._request_step()):
            while True:
                try:
                    _klines = self._broker.get_klines(
                        self._time_frame, since=timestamp
                    )
                    klines = klines.append(_klines, ignore_index=True)
                    break

                except Exception as e:  # Usually connection issues.
                    # TODO: To logger instead print
                    print("Fail, due the error: ", e)
                    time.sleep(5)  # 5 sec cooldown time.

            if self._append_to_storage:
                table = "{}_{}".format(
                    self.market.broker_name,
                    self.market.ticker_symbol.lower(),
                )
                storage = StorageKlines(
                    table=table, database=self.storage_name
                )
                storage.append(_klines)

            if self._broker.was_request_limit_reached():
                time.sleep(10)  # 10 sec cooldown time.
                # TODO: To logger instead print
                print("Sleeping cause request limit was hit.")

        return klines


class FromStorage(KlinesFrom):
    """Ponto de entrada para solicitações de klines a partir do armazenamento.
    É capaz de gerar candles sintéticos, de QUALQUER time frame, a partir de
    klines armazenadas com timeframes mais refinados, graças às qualidades do
    influxdb
    """

    __slots__ = [
        "storage",
    ]

    def __init__(self, market: Market, time_frame: str, storage_name: str):
        table = "{}_{}".format(
            market.broker_name.capitalize(), (market.ticker_symbol).lower()
        )
        self.storage = StorageKlines(table=table, database=storage_name)
        super().__init__(market, time_frame)

    def oldest_open_time(self) -> int:  #! Refactor this?
        return self.storage.seconds_timestamp_of_oldest_record(self.time_frame)

    def newest_open_time(self) -> int:
        return self.storage.seconds_timestamp_of_newest_record(self.time_frame)

    def _get_core(self, since: int, until: int) -> pd.core.frame.DataFrame:

        try:
            return self.storage.get(since, until, self.time_frame)

        except Exception as e:  #!TODO: Log instead print
            print("Fail to get klines from storage due to {}".format(e))
            return pd.DataFrame()


class ToStorage:
    __slots__ = [
        "storage",
        "klines_getter",
    ]

    def __init__(self, market: Market):
        self.klines_getter = FromBroker(market)
        self.klines_getter._append_to_storage = True

    def create_largest_refined_backtesting(self):
        self.klines_getter.storage_name = "backtesting_klines"

        since = self.klines_getter.oldest_open_time()
        until = self.klines_getter.newest_open_time()

        raw_klines = self.klines_getter.get(since=since, until=until)
        return raw_klines


class PriceFromStorage:
    def __init__(self, market: Market, price_metrics="ohlc4"):
        self.klines_getter = FromStorage(
            market, time_frame="1m", storage_name="backtesting_klines"
        )
        self.price_metrics = price_metrics

    def get_price_at(self, desired_datetime: DateTimeType) -> float:
        desired_datetime = sanitize_input_datetime(desired_datetime)

        klines = self.klines_getter.get(
            since=desired_datetime - 60000, until=desired_datetime + 60000
        )
        klines.apply_indicator.trend.price_from_kline(self.price_metrics)
        price_column = getattr(klines, "Price_{}".format(self.price_metrics))
        return price_column.iloc[1001].item()


def klines_getter(market: Market, time_frame: str = "", backtesting=False):
    if backtesting:
        return FromStorage(
            market, time_frame, storage_name="backtesting_klines"
        )
    return FromBroker(market, time_frame)
