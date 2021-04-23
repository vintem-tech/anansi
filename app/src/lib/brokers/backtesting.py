from .binance import Binance

from .base import Broker, DocInherit, DF, Order


class BackTestingBroker(Broker):
    def __init__(self, operation, real_broker):
        super().__init__()
        self.operation = operation
        self.real_broker = real_broker

    @DocInherit
    def server_time(self) -> int:
        pass

    @DocInherit
    def max_requests_limit_hit(self) -> bool:
        pass

    @DocInherit
    def get_klines(self, ticker_symbol: str, time_frame: str, **kwargs) -> DF:
        pass

    @DocInherit
    def get_price(self, ticker_symbol: str, **kwargs) -> float:
        raise NotImplementedError

    @DocInherit
    def ticker_info(self, ticker_symbol: str) -> dict:
        raise NotImplementedError

    @DocInherit
    def free_quantity_asset(self, asset_symbol: str) -> float:
        raise NotImplementedError

    @DocInherit
    def min_notional(self, ticker_symbol: str) -> float:
        raise NotImplementedError

    @DocInherit
    def minimal_order_quantity(self, ticker_symbol) -> float:
        raise NotImplementedError

    @DocInherit
    def execute_order(self, order: Order):
        raise NotImplementedError

    @DocInherit
    def execute_test_order(self, order: Order):
        raise NotImplementedError


class BinanceBacktesting(BackTestingBroker):
    def __init__(self, operation):
        super().__init__(operation, real_broker=Binance())

    @DocInherit
    def server_time(self) -> int:
        pass

    @DocInherit
    def max_requests_limit_hit(self) -> bool:
        pass

    @DocInherit
    def get_klines(self, ticker_symbol: str, time_frame: str, **kwargs) -> DF:
        pass

    @DocInherit
    def get_price(self, ticker_symbol: str, **kwargs) -> float:
        raise NotImplementedError

    @DocInherit
    def ticker_info(self, ticker_symbol: str) -> dict:
        raise NotImplementedError

    @DocInherit
    def free_quantity_asset(self, asset_symbol: str) -> float:
        raise NotImplementedError

    @DocInherit
    def min_notional(self, ticker_symbol: str) -> float:
        raise NotImplementedError

    @DocInherit
    def minimal_order_quantity(self, ticker_symbol) -> float:
        raise NotImplementedError

    @DocInherit
    def execute_order(self, order: Order):
        raise NotImplementedError

    @DocInherit
    def execute_test_order(self, order: Order):
        raise NotImplementedError
