"""Entrypoint for instantiating a broker"""

import sys

from . import base, binance, backtesting

thismodule = sys.modules[__name__]


def get_broker(broker_name: str) -> base.Broker:
    """Given a market ticker, returns an instantiated broker"""

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
