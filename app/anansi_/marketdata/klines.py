import time
import pandas as pd
import pendulum
from . import indicators
from ..brokers.brokers import get_broker
from ..share.schemas import Market, TimeFormat
from ..share.tools import ParseDateTime, sanitize_input_datetime, seconds_in
from ..share.storage import StorageKlines

pd.options.mode.chained_assignment = None


def klines_getter(market: Market, time_frame: str = "", backtesting=False):
    if backtesting:
        return FromStorage(
            market, time_frame, storage_name="backtesting_klines"
        )
    return FromBroker(market, time_frame)


@pd.api.extensions.register_dataframe_accessor("KlinesDateTime")
class KlinesDateTime:
    def __init__(self, klines: pd.core.frame.DataFrame):
        self._klines = klines

    def from_human_readable_to_timestamp(self):
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
    def __init__(self, klines):
        self._klines = klines
        self.trend = indicators.Trend(self._klines)
        self.momentum = indicators.Momentum(self._klines)
        self.volatility = indicators.Volatility(self._klines)
        self.volume = indicators.Volume(self._klines)


class KlinesFrom:
    """Parent class of FromBroker and Fromstorage"""

    __slots__ = [
        "broker_name",
        "ticker_symbol",
        "time_frame",
    ]

    def __init__(self, market: Market, time_frame: str):
        self.broker_name = market.broker_name
        self.ticker_symbol = market.ticker_symbol.upper()
        self.time_frame = time_frame

    def _now(self) -> int:
        return (pendulum.now(tz="UTC")).int_timestamp

    def seconds_timeframe(self) -> int:
        return seconds_in(self.time_frame)

    def oldest_open_time(self) -> int:
        raise NotImplementedError

    def newest_open_time(self) -> int:
        raise NotImplementedError

    def _get_core(
        self, start_time: int, end_time: int
    ) -> pd.core.frame.DataFrame:
        raise NotImplementedError

    # TODO: Sanitize since/until to avoid ValueError until < since
    def _calculate_until_from_since_and_n(
        self, since: int, number_of_candles: int
    ) -> int:
        until = (number_of_candles + 1) * self.seconds_timeframe() + since
        return (
            until
            if until <= self.newest_open_time()
            else self.newest_open_time()
        )

    def _calculate_since_from_until_and_n(
        self, until: int, number_of_candles: int
    ) -> int:
        since = until - (number_of_candles + 1) * self.seconds_timeframe()
        return (
            since
            if since >= self.oldest_open_time()
            else self.oldest_open_time()
        )

    def _get_given_n_and_until(
        self, number_of_candles: int, until: int
    ) -> pd.core.frame.DataFrame:
        since = self._calculate_since_from_until_and_n(
            until, number_of_candles
        )
        _klines = self._get_core(start_time=since, end_time=until)
        return _klines[_klines.Open_time <= until][-number_of_candles:]

    def _get_given_n_and_since(
        self, number_of_candles: int, since: int
    ) -> pd.core.frame.DataFrame:
        until = self._calculate_until_from_since_and_n(
            since, number_of_candles
        )
        _klines = self._get_core(start_time=since, end_time=until)
        return _klines[_klines.Open_time >= since][:number_of_candles]

    def _get_given_since_and_until(
        self, since: int, until: int
    ) -> pd.core.frame.DataFrame:
        _klines = self._get_core(start_time=since, end_time=until)
        return _klines[_klines.Open_time <= until]

    def get(self, **kwargs) -> pd.core.frame.DataFrame:
        since = kwargs.get("since")
        until = kwargs.get("until")
        number_of_candles: int = kwargs.get("number_of_candles")

        if since:
            since = sanitize_input_datetime(since)
        if until:
            until = sanitize_input_datetime(until)

        klines = (
            self._get_given_since_and_until(since, until)
            if since and until and not number_of_candles
            else self._get_given_n_and_since(number_of_candles, since)
            if number_of_candles and since and not until
            else self._get_given_n_and_until(number_of_candles, until)
            if number_of_candles and until and not since
            else pd.DataFrame()
        )  # Errors imply an empty dataframe

        klines.KlinesDateTime.from_timestamp_to_human_readable()
        return klines

    def oldest(self, number_of_candles=1) -> pd.core.frame.DataFrame:
        return self.get(
            number_of_candles=number_of_candles, since=self.oldest_open_time()
        )

    def newest(self, number_of_candles=1) -> pd.core.frame.DataFrame:
        return self.get(
            number_of_candles=number_of_candles, until=self.newest_open_time()
        )


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
        "_storage_name",
    ]

    def __init__(self, market: Market, time_frame: str = str()):
        self._broker = get_broker(market.broker_name)
        super(FromBroker, self).__init__(market, time_frame)
        self._time_frame = self._validate_tf(time_frame)
        self._append_to_storage: bool = False
        self._storage_name: str = str()

    def _validate_tf(self, tf: str):
        tf_list = self._broker.possible_time_frames
        if tf:
            if tf in tf_list:
                return tf
            else:
                raise ValueError("Time frame must be in {}".format(tf_list))
        else:
            return tf_list[0]

    @property
    def time_frame(self):
        return self._time_frame

    @time_frame.setter
    def time_frame(self, time_frame_to_set):
        tf = self._validate_tf(time_frame_to_set)
        self._time_frame = tf

    def oldest_open_time(self) -> int:
        oldest_candle = self._broker.get_klines(
            ticker_symbol=self.ticker_symbol,
            time_frame=self._time_frame,
            since=1,
            number_of_candles=1,
        )
        return oldest_candle.Open_time.item()

    def newest_open_time(self) -> int:
        return (pendulum.now(tz="UTC")).int_timestamp

    def _request_step(self) -> int:
        return self._broker.records_per_request * self.seconds_timeframe()

    def _get_core(
        self, start_time: int, end_time: int
    ) -> pd.core.frame.DataFrame:

        klines = pd.DataFrame()

        for timestamp in range(start_time, end_time + 1, self._request_step()):
            while True:
                try:
                    _klines = self._broker.get_klines(
                        self.ticker_symbol, self._time_frame, since=timestamp
                    )
                    klines = klines.append(_klines, ignore_index=True)
                    break

                except Exception as e:  # Usually connection issues.
                    # TODO: To logger instead print
                    print("Fail, due the error: ", e)
                    time.sleep(5)  # 60 sec cooldown time.

            if self._append_to_storage:
                table = "{}_{}".format(
                    self.broker_name,
                    self.ticker_symbol.lower(),
                    # self._time_frame # Não faz sentido o nome da tabela
                    # conter o timeframe, já que o storage
                    # deve resolver a agregação, a despeito
                    # de qual seja o mínimo timeframe
                    # armazenado
                )
                storage = StorageKlines(
                    table=table, database=self._storage_name
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
            market.broker_name, market.ticker_symbol.lower()
        )
        self.storage = StorageKlines(table=table, database=storage_name)
        super(FromStorage, self).__init__(market, time_frame)

    def oldest_open_time(self) -> int:
        return self.storage._seconds_timestamp_of_oldest_record()

    def newest_open_time(self) -> int:
        return self.storage._seconds_timestamp_of_newest_record()

    def _get_core(
        self, start_time: int, end_time: int
    ) -> pd.core.frame.DataFrame:

        try:
            return self.storage.get_klines(
                start_time, end_time, self.time_frame
            )

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
        self.klines_getter._storage_name = "backtesting_klines"

        start_time = self.klines_getter.oldest_open_time()
        end_time = self.klines_getter.newest_open_time()

        raw_klines = self.klines_getter.get(since=start_time, until=end_time)
        return raw_klines


class PriceFromStorage:
    def __init__(self, market: Market, price_metrics="ohlc4"):
        self.klines_getter = FromStorage(
            market, time_frame="1m", storage_name="backtesting_klines"
        )
        self.price_metrics=price_metrics

    def get_price_at(self, desired_datetime: TimeFormat) -> float:
        desired_datetime = sanitize_input_datetime(desired_datetime)
        
        klines = self.klines_getter.get(
            since=desired_datetime - 60000, until=desired_datetime + 60000
        )
        klines.apply_indicator.trend.price_from_kline(self.price_metrics)
        price_column = getattr(klines, "Price_{}".format(self.price_metrics))
        return price_column.iloc[1001].item()
