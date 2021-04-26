"""All needed functions, wrapping the communication with binance"""

# pylint: disable=too-few-public-methods

from decimal import Decimal

from binance.client import Client as BinanceClient
from binance.exceptions import BinanceOrderException

# from ...config.settings import BinanceSettings
from .base import (
    DF,
    Broker,
    BrokerSettings,
    Order,
    Quantity,
    DocInherit,
    formatting,
    get_response,
)


class BinanceSettings(BrokerSettings):
    """
    https://github.com/binance-exchange/binance-official-api-docs/blob/master/rest-api.md
    """

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


class Binance(Broker):
    """All needed functions, wrapping the communication with binance"""

    def __init__(self, settings=BinanceSettings()):
        super().__init__(settings)
        self.client = None

    @DocInherit
    def server_time(self) -> int:
        endpoint = self.settings.time_endpoint
        time_str = (get_response(endpoint)).json()["serverTime"]
        return int(float(time_str) / 1000)

    @DocInherit
    def max_requests_limit_hit(self) -> bool:
        ping_endpoint = self.settings.ping_endpoint
        request_weight_per_minute = self.settings.request_weight_per_minute
        requests_on_current_minute = int(
            (get_response(ping_endpoint)).headers["x-mbx-used-weight-1m"]
        )
        if requests_on_current_minute >= request_weight_per_minute:
            return True
        return False

    @DocInherit
    def get_klines(self, ticker_symbol: str, time_frame: str, **kwargs) -> DF:
        since: int = kwargs.get("since")
        until: int = kwargs.get("until")
        number_of_candles: int = kwargs.get("number_of_candles")

        endpoint = self.settings.klines_endpoint.format(
            ticker_symbol, time_frame
        )

        if since:
            endpoint += "&startTime={}".format(str(since * 1000))
        if until:
            endpoint += "&endTime={}".format(str(until * 1000))
        if number_of_candles:
            endpoint += "&limit={}".format(str(number_of_candles))

        raw_klines = (get_response(endpoint)).json()

        klines = formatting.FormatKlines(
            time_frame,
            raw_klines,
            datetime_format=self.settings.datetime_format,
            datetime_unit=self.settings.datetime_unit,
            columns=self.settings.kline_information,
        ).to_dataframe()

        if self.settings.show_only_desired_info:
            return klines[self.settings.klines_desired_informations]
        return klines

    @DocInherit
    def get_price(self, ticker_symbol, **kwargs) -> float:
        return float(self.client.get_avg_price(symbol=ticker_symbol)["price"])

    @DocInherit
    def ticker_info(self, ticker_symbol: str) -> dict:
        return self.client.get_symbol_info(symbol=ticker_symbol)

    def create_client(self, api_key: str, api_secret: str):
        self.client = BinanceClient(api_key=api_key, api_secret=api_secret)

    @DocInherit
    def free_quantity_asset(self, asset_symbol: str) -> float:
        return float(self.client.get_asset_balance(asset=asset_symbol)["free"])

    @DocInherit
    def min_notional(self, ticker_symbol: str) -> float:
        ticker_info = self.ticker_info(ticker_symbol)

        return float(ticker_info["filters"][3]["minNotional"])

    @DocInherit
    def minimal_order_quantity(self, ticker_symbol: str) -> float:
        min_notional = self.min_notional(ticker_symbol)
        price = self.get_price(ticker_symbol)

        return 1.03 * min_notional / price

    def _sanitize_quantity(self, quantity: float) -> Quantity:
        quantity = Quantity()
        ticker_info = self.ticker_info(self.ticker_symbol)
        minimum_quantity_filter = float(ticker_info["filters"][2]["minQty"])

        quantity_ = Decimal.from_float(quantity).quantize(
            Decimal(str(minimum_quantity_filter))
        )
        minimum_quantity = self.minimal_order_quantity(self.ticker_symbol)
        sufficient_balance = float(quantity_) > minimum_quantity

        if sufficient_balance:
            quantity.is_sufficient = True
            quantity.value = str(quantity_)

        return quantity

    def _sanitize_price(self, price: float) -> str:
        ticker_info = self.ticker_info(self.ticker_symbol)
        price_filter = float(ticker_info["filters"][0]["tickSize"])
        price_ = Decimal.from_float(price).quantize(Decimal(str(price_filter)))

        return str(price_)

    def _check_order_and_update(self, order: Order) -> Order:
        order_ = self.client.get_order(
            symbol=self.ticker_symbol, orderId=order.id_by_broker
        )
        quote_amount = float(order_["executedQty"])
        base_amount = float(order_["cummulativeQuoteQty"])

        order.price = base_amount / quote_amount
        order.timestamp = int(float(order_["time"]) / 1000)
        order.fulfilled = True
        order.quantity = quote_amount
        order.fee = self.settings.fee_rate_decimal * base_amount

        return order

    @DocInherit
    def execute_order(self, order: Order) -> Order:
        signal = order.interpreted_signal

        if signal == "hold":
            order.warnings = "By pass due to hold signal"
            return order

        execution_method = "order_{}_{}".format(signal, order.order_type)
        order_executor_client = getattr(self.client, execution_method)

        quantity = self._sanitize_quantity(order.quantity)
        if quantity.is_sufficient:
            order_payload = dict(
                symbol=self.ticker_symbol, quantity=quantity.value
            )
            if order.order_type == "limit":
                order_payload = dict(
                    order_payload, price=self._sanitize_price(order.price)
                )

            try:
                fulfilled_order = order_executor_client(**order_payload)
                order.id_by_broker = fulfilled_order["orderId"]
                order = self._check_order_and_update(order)

            except BinanceOrderException as broker_erro:
                order.warnings = str(broker_erro)

            return order

        order.warnings = "Insufficient balance"
        return order

    @DocInherit
    def execute_test_order(self, order: Order):
        pass
