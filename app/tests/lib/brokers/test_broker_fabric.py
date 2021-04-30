"""Test the fabric and get_backtesting_broker functions"""

# pylint: disable=missing-function-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=too-few-public-methods

import pytest
from src.lib.brokers import fabric


def test_implemented_broker():
    broker_name = "binance"
    broker = fabric(broker_name)
    assert broker.__class__.__name__ == broker_name.capitalize()

def test_for_a_not_implemented_broker():
    with pytest.raises(NotImplementedError):
        broker_name = "not_implemented"
        fabric(broker_name)

class TestGetBackTestingBroker:
    pass
