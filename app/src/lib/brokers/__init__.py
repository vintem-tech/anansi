"""Entrypoint for instantiating a broker"""

import sys

from . import base, binance, backtesting

thismodule = sys.modules[__name__]


def get_broker(broker_name: str) -> base.Broker:
    """Returns a instatiate broker, if 'broker_name' matches an
    implemented broker

    :param broker_name: The name of desired broker
    :type broker_name: str
    :raises NotImplementedError: If broker name is not recognized
    as an implemented broker
    :return: A broker
    :rtype: base.Broker
    """

    try:
        module = getattr(thismodule, broker_name.lower())
        class_ = broker_name.capitalize()

        return getattr(module, class_)()

    except AttributeError as err:
        err_msg = "Not implented '{}' broker.".format(broker_name)
        raise NotImplementedError(err_msg) from err


def get_backtesting_broker(operation):
    return getattr(
        backtesting, "{}Backtesting".format(operation.broker.capitalize())
    )(operation)
