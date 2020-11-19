def get_settings():
    return DefaultSettings()


class Exchange:
    DateTimeFmt = "timestamp"
    DateTimeUnit = "seconds"
    base_endpoint = ""
    ping_endpoint = base_endpoint + "ping"
    time_endpoint = base_endpoint + "time"
    klines_endpoint = base_endpoint + "klines?symbol={}&interval={}"
    request_weight_per_minute: int = None
    records_per_request: int = None
    possible_candle_periods = [
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
    fee_rate_decimal = 0.001
    kline_information = [
        # Which information (in order), about each candle,
        # is returned by Binance
        "Open_time",
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    ]


class Binance(Exchange):
    """
    https://github.com/binance-exchange/binance-official-api-docs/blob/master/rest-api.md
    """

    DateTimeFmt = "timestamp"
    DateTimeUnit = "milliseconds"
    base_endpoint = "https://api.binance.com/api/v3/"
    request_weight_per_minute = 1100  # Default: 1200/min/IP
    records_per_request = 500  # Default: 500 | Limit: 1000 samples/response
    kline_information = Exchange.kline_information + [
        "Close_time",
        "Quote_asset_volume",
        "Number_of_trades",
        "Taker_buy_base_asset_volume",
        "Taker_buy_quote_asset_volume",
        "Ignore",
    ]


class DefaultSettings:
    exchange = Binance()
