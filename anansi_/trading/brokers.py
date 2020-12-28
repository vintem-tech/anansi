import sys
from binance.client import Client as BinanceClient
from binance.enums import TIME_IN_FORCE_GTC
from .schemas import Market, Order, Portfolio

thismodule = sys.modules[__name__]


def get_broker(market: Market):
    broker_name = market.broker_name.capitalize()

    return getattr(thismodule, "{}Broker".format(broker_name))(market)


api_key = "f3OO0BGKIFxz1en2DM3YSMVVCjNCB0cuKCyfLTnPkWUzDXtdOCdV0vkfljoXeTTV"
api_secret = "XNYKdj3Y39EgcB9JI2bwZ2BgHhZYsI4OvEH3muO1zOTbD2Q8v6Ul8dlMZbNUDdI4"


class BinanceBroker:
    def __init__(self, market: Market):
        self.market = market
        self.fee_rate_decimal: float = 0.001
        self.client = BinanceClient(api_key=api_key, api_secret=api_secret)
        self.minimal_base_amount = float(
            self.client.get_symbol_info(symbol=market.ticker_symbol)[
                "filters"
            ][3]["minNotional"]
        )
        self.precision = int(
            self.client.get_symbol_info(symbol=market.ticker_symbol)[
                "quoteAssetPrecision"
            ]
        )
        self.minimal_amount = float(
            self.client.get_symbol_info(symbol=market.ticker_symbol)[
                "filters"
            ][2]["minQty"]
        )

    def price(self) -> float:
        ticker_symbol = self.market.ticker_symbol
        return float(self.client.get_avg_price(symbol=ticker_symbol)["price"])

    def portfolio(self) -> float:
        p = Portfolio()
        p.quote, p.base = (
            float(self.client.get_asset_balance(asset=symbol)["free"])
            for symbol in [self.market.quote_symbol, self.market.base_symbol]
        )
        return p

    def execute(self, order: Order):
        executor = self.client.create_order
        if order.test_order:
            executor = self.client.create_test_order

        order_payload = dict(
            symbol=order.ticker_symbol,
            side=order.side,
            type=order.order_type,
            quantity=order.quantity,
        )
        _order = executor(**order_payload)
        return _order
