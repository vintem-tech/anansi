import sys
import pandas as pd
import pendulum
import requests
from ..share.tools import DocInherit, FormatKlines
from .settings import get_settings, Exchange

thismodule = sys.modules[__name__]
settings = get_settings()
doc_inherit = DocInherit


def instantiate_broker(broker_name: str) -> Exchange:
    return getattr(thismodule, broker_name.capitalize())()


def get_response(endpoint: str) -> requests.models.Response:
    try:
        with requests.get(endpoint) as response:
            if response.status_code == 200:
                return response
    except Exception as e:
        raise ConnectionError(
            "Could not establish a broker connection. Details: {}".format(e)
        )


def remove_last_if_unclosed(klines: pd.DataFrame) -> pd.DataFrame:
    last_open_time = klines[-1:].Open_time.item()
    delta_time = (pendulum.now(tz="UTC")).int_timestamp - last_open_time
    unclosed = bool(delta_time < klines.attrs["SecondsTimeFrame"])

    if unclosed:
        return klines[:-1]
    return klines


class Broker(settings.exchange):
    def server_time(self) -> int:
        """Date time of broker server.

        Returns (int): Seconds timestamp
        """
        raise NotImplementedError

    def was_request_limit_reached(self) -> bool:
        """Boolean test to verify if the request limit, in the current
        minute (for a given IP), has been reached.

        Returns (bool): Hit the limit?
        """
        raise NotImplementedError

    def get_klines(self, **kwargs) -> pd.DataFrame:
        """Historical market data (candlesticks, OHLCV).

        Returns (pd.DataFrame): N lines DataFrame, where 'N' is the number of
        candlesticks returned by broker, which must be less than or equal to
        the '_LIMIT_PER_REQUEST' parameter, defined in the broker's settings
        (settings module). The dataframe columns represents the information
        provided by the broker, declared by the parameter 'kline_information'
        (settings, on the broker settings class).
        """

        raise NotImplementedError


class Binance(Broker):
    @doc_inherit
    def __init__(self):
        super(Binance, self).__init__()

    @doc_inherit
    def server_time(self) -> int:
        return int(
            float((get_response(self.time_endpoint)).json()["serverTime"])
            / 1000
        )

    @doc_inherit
    def was_request_limit_reached(self) -> bool:
        requests_on_current_minute = int(
            (get_response(self.ping_endpoint)).headers["x-mbx-used-weight-1m"]
        )
        if requests_on_current_minute >= self.request_weight_per_minute:
            return True

        return False

    @doc_inherit
    def get_klines(
        self,
        ticker_symbol: str,
        time_frame: str,
        ignore_opened_candle: bool = True,
        show_only_desired_info: bool = True,
        **kwargs
    ) -> pd.DataFrame:
        """
        Args:
            ticker_symbol (str): 'BTCUSDT', for example.
            time_frame (str): '1m', '2h', '1d'...
            ignore_opened_candle (bool, optional): Defaults to True
            show_only_desired_info (bool, optional): Defaults to True.

        **kwargs:
            number_of_candles (int): Number or desired candelesticks
            for request; must to respect the broker limits.

            It's possible to pass timestamps (seconds):
            since (int): Open_time of the first candlestick on desired series
            until (int): Open_time of the last candlestick on desired series
        """

        since: int = kwargs.get("since")
        until: int = kwargs.get("until")
        number_of_candles: int = kwargs.get("number_of_candles")
        endpoint = self.klines_endpoint.format(ticker_symbol, time_frame)

        if since:
            endpoint += "&startTime={}".format(str(since * 1000))
        if until:
            endpoint += "&endTime={}".format(str(until * 1000))
        if number_of_candles:
            endpoint += "&limit={}".format(str(number_of_candles))
        raw_klines = (get_response(endpoint)).json()

        klines = FormatKlines(
            time_frame,
            raw_klines,
            DateTimeFmt=self.DateTimeFmt,
            DateTimeUnit=self.DateTimeUnit,
            columns=self.kline_information,
        ).to_dataframe()

        if ignore_opened_candle:
            klines = remove_last_if_unclosed(klines)

        if show_only_desired_info:
            return klines[settings.klines_desired_informations]
        return klines
