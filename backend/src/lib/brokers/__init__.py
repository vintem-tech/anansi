"""Entrypoint for instantiating a broker"""

import sys
from typing import List, Union
from . import base, binance, backtesting
from ...utils.schemas import OperationalModes

modes = OperationalModes()

thismodule = sys.modules[__name__]

implemented_brokers = [
    "b3",
    "binance",
]

class Fabric:
    """Returns an instatiate broker, if 'broker' matches an
    implemented broker

    :param broker: The name of desired broker
    :type broker: str
    :raises NotImplementedError: If broker name is not implemented yet
    """

    __slots__ = ["real_broker"]

    def __init__(self, broker_name: str):
        self.real_broker = None
        try:
            broker_name_ = "_{}".format(broker_name.lower())
            self.real_broker = getattr(self, broker_name_)()

        except AttributeError as error:
            err_msg = "Not implented '{}' broker.".format(broker_name)
            raise NotImplementedError(err_msg) from error

    @staticmethod
    def _binance() -> binance.Binance:
        return binance.Binance()

    def real(self) -> base.Broker:
        """Returns a 'real' 'Broker' instance, capable of communicating
        directly with the broker, in order to query market data, or even
        access validated endpoints to send trading orders and checking
        balance.

        :return: A 'real' broker
        :rtype: base.Broker
        """

        return self.real_broker

    def backtesting(self, assets: List[str]) -> backtesting.BackTestingBroker:
        """A 'Broker' backtesting, with  very similar methods to the
        'real' 'Broker' but specifically designed to play a role in the
        'artificial orders' triggering flow ('trading' package). For
        while, the subpackage 'marketdata' keeping doing the market data
        query, on backtesting mode scenario

        :param assets: A list of assets whose pertinent information must
                       be consulted and 'saved' in memory
        :type assets: List[str]
        :return: A backtesting Broker
        :rtype: backtesting.BackTestingBroker
        """

        return backtesting.BackTestingBroker(self.real_broker, assets)
