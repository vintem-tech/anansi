# pylint: disable=too-few-public-methods

from typing import List, Union

from ..lib.utils.databases.sql.models import BackTestingOperation
from ..lib.trading.main import Trader
from ..lib.utils.schemas import Ticker
from ..config.setups import OperationalSetup


class BinanceMonitoring:
    """Binance monitored markets"""

    bases: list = [
        "BTC",
        "ETH",
        "NEO",
        #        "LINK",
        #        "EOS",
        #        "LTC",
        #        "XRP",
        #        "BNB",
        #        "ADA",
        #        "TRX",
    ]
    quotes: list = ["USDT", "BTC"]

    def tickers(self) -> List[Ticker]:
        """Returns a list of binance market tickers to monitoring"""

        return [
            Ticker(
                symbol="{}{}".format(base, quote),
                base=base,
                quote=quote,

            )
            for quote in self.quotes
            for base in self.bases
            if quote != base
        ]


class BackTesting:
    operations = dict()
    traders = list()

    def create_operation(
        self,
        name: str,
        broker="binance",
        tickers_list=BinanceMonitoring().tickers(),
        setup=OperationalSetup().json(),
    ) -> BackTestingOperation:
        return BackTestingOperation.create(name, broker, tickers_list, setup)

    def get_operations(self) -> List[str]:
        operations_ = BackTestingOperation.select()
        if operations_:
            self.operations = {
                operation.name: operation for operation in operations_
            }

        return self.operations

    def get_a_trader(self, operation_name: str) -> Union[Trader, None]:
        if operation_name in list(self.operations.keys()):
            try:
                return Trader(operation=self.operations.get(operation_name))

            except BaseException as error:
                raise Exception(error) from BaseException

        raise KeyError("{} not found".format(operation_name))
