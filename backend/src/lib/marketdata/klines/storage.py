# pylint: disable=too-few-public-methods

from ....utils.exceptions import KlinesError, StorageError
from ....utils.schemas.legacy import Ticker, DateTimeType
from ....utils.tools.time_handlers import ParseDateTime, int_timestamp
from .base import DF, Getter
from .from_broker import GetterFromBroker


class GetterFromStorage(Getter):
    """Entrypoint for requests to the stored klines"""

    def __init__(self, broker_name: str, ticker: Ticker, time_frame: str):
        super().__init__(broker_name, ticker, time_frame)

    def oldest_open_time(self) -> int:
        return self.storage.oldest_open_time()

    def newest_open_time(self) -> int:
        return self.storage.newest_open_time()

    def _get_core(self, since: int, until: int) -> DF:
        try:
            return self.storage.get_by_time_range(since, until)
        except StorageError as err:
            raise Exception.with_traceback(err) from StorageError


class ToStorage:
    """Entrypoint to append klines to StorageKlines"""

    __slots__ = ["klines_getter"]

    def __init__(self, broker_name: str, ticker: Ticker, time_frame: str):
        self.klines_getter = GetterFromBroker(broker_name, ticker, time_frame)
        self.klines_getter.store_klines_round_by_round = True

    def create_backtesting(
        self, since: DateTimeType, until: DateTimeType
    ) -> DF:
        """Requests the intended mass of data from the broker, saving
        them in each cycle.

        Args:
            since (DateTimeType): Start desired datetime
            until (DateTimeType): End desired datetime

        Returns:
            pd.core.frame.DataFrame: Raw timestamp formatted OHLCV
            (klines) dataframe
        """

        return self.klines_getter.get(since=since, until=until)


class PriceFromStorage:
    """Useful for backtesting scenarios, in order to be able to emulate
    the instant price at any past time; to do so, uses the finer-grained
    klines. The mass of requested klines is extensive (approximately 16h
    backwards and 16h forwards) since, as 'StorageKlines' takes care of
    the interpolation, it is prudent to predict long missing masses of
    data."""

    def __init__(
        self, broker_name: str, ticker: Ticker, price_metrics="ohlc4"
    ):
        self.klines_getter = GetterFromBroker(
            broker_name, ticker, time_frame="1m"
        )
        self.price_metrics = price_metrics

    def _valid_timestamp(self, timestamp: int) -> bool:
        return bool(timestamp <= self.klines_getter.newest_open_time())

    def get_price_at(self, desired_datetime: DateTimeType) -> float:
        """A 'fake' past ticker price"""

        desired_datetime = int_timestamp(desired_datetime)

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
                    ).to_human_readable()
                )
            )
