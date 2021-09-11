from .base import Broker, DocInherit, DF, Order
from typing import List

class BackTestingBroker(Broker):
    def __init__(self, real_broker:Broker, assets:List[str]):
        super().__init__()
        self.real_broker = real_broker
        self.assets = assets
        #self._create_cache()

    def _create_cache(self):
        pass

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
