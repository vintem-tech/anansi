"""Entrypoint for instantiating a broker"""

import sys
from typing import List
from . import base, binance, backtesting

thismodule = sys.modules[__name__]


def fabric(broker: str) -> base.Broker:
    """Returns an instatiate broker, if 'broker' matches an
    implemented broker

    :param broker: The name of desired broker
    :type broker: str
    :raises NotImplementedError: If broker name is not recognized
    as an implemented broker
    :return: A broker
    :rtype: base.Broker
    """

    try:
        module = getattr(thismodule, broker.lower())
        class_ = broker.capitalize()

        return getattr(module, class_)()

    except AttributeError as err:
        err_msg = "Not implented '{}' broker.".format(broker)
        raise NotImplementedError(err_msg) from err


def backtesting_fabric(broker:str, assets:List[str]) -> base.Broker:
    """[summary]

    :param broker: [description]
    :type broker: str
    :param assets: [description]
    :type assets: List[str]
    :raises NotImplementedError: [description]
    :return: [description]
    :rtype: base.Broker
    """

    try:
        real_broker = fabric(broker)
        backtesting_broker = getattr(backtesting, "BackTestingBroker")
        return backtesting_broker(real_broker, assets)

    except AttributeError as err:
        err_msg = "Not implented '{}' broker.".format(broker)
        raise NotImplementedError(err_msg) from err
