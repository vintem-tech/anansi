# pylint: disable=too-few-public-methods

from ....utils.exceptions import KlinesError, StorageError
from ....utils.schemas.generics import Ticker, DateTimeType
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


class ScrapingFromBrokerToStorage:
    """Entrypoint to append klines to StorageKlines"""

    __slots__ = ["klines_getter"]

    def __init__(self, broker_name: str, ticker: Ticker, time_frame: str):
        self.klines_getter = GetterFromBroker(broker_name, ticker, time_frame)
        self.klines_getter.store_klines_round_by_round = True

    def append_time_range(
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
