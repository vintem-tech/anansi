# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument
# pylint: disable=too-few-public-methods

"""All brokers configuration must to be placed here"""

from environs import Env
from pydantic import BaseModel

env = Env()

#! TODO: change API key
BINANCE_API_KEY = (
    "rjp1jPSMK1XSvFAv8HzhnpOoWFmyH9XmPQ6Rj3r1RB29VuPWGWy5uRhL4XysHoVw"
)
BINANCE_API_SECRET = (
    "f5biQUiVqNhK33zPLkmJmn3bzVX7azrENNvWHPNuNyy2cX7XgwLCSq2ZTTc498Qj"
)

class BrokerSettings(BaseModel):
    """Broker parent class """

    api_key: str = str()
    api_secret: str = str()
    datetime_format: str = "timestamp"
    datetime_unit: str = "seconds"
    base_endpoint: str = str()
    ping_endpoint: str = str()
    time_endpoint: str = str()
    klines_endpoint: str = str()
    request_weight_per_minute: int = None
    records_per_request: int = None
    possible_time_frames: list = [
        "1m",
        "3m",
        "5m",
        "15m",
        "30m",
        "1h",
        "2h",
        "4h",
        "6h",
        "8h",
        "12h",
        "1d",
        "3d",
        "1w",
        "1M",
    ]
    kline_information: list = [
        "Open_time",
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
        "Close_time",
    ]
    klines_desired_informations: list = kline_information[:-1]
    ignore_opened_candle: bool = True
    show_only_desired_info: bool = True
    fee_rate_decimal: float = 0.001


class BinanceSettings(BrokerSettings):
    """
    https://github.com/binance-exchange/binance-official-api-docs/blob/master/rest-api.md
    """

    api_key: str = env.str("BINANCE_API_KEY", default=BINANCE_API_KEY)
    api_secret:str = env.str("BINANCE_API_SECRET", default=BINANCE_API_SECRET)
    datetime_unit = "milliseconds"
    base_endpoint = "https://api.binance.com/api/v3/"
    ping_endpoint = base_endpoint + "ping"
    time_endpoint = base_endpoint + "time"
    klines_endpoint = base_endpoint + "klines?symbol={}&interval={}"
    request_weight_per_minute = 1100  # Default: 1200/min/IP
    records_per_request = 500  # Default: 500 | Limit: 1000 samples/response))

    # Which information (IN ORDER!), about each candle, is returned by Binance
    kline_information = BrokerSettings().kline_information + [
        "Quote_asset_volume",
        "Number_of_trades",
        "Taker_buy_base_asset_volume",
        "Taker_buy_quote_asset_volume",
        "Ignore",
    ]
