"""Test the fabric and get_backtesting_broker functions"""

# pylint: disable=missing-function-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=too-few-public-methods

import pytest
from src.lib.brokers_wrappers import BrokerFabric

@pytest.mark.parametrize("name", ["binance"])
def test_for_a_implemented_broker(name:str):
    broker = BrokerFabric(broker_name=name).real()
    assert broker.__class__.__name__ == name.capitalize()

@pytest.mark.parametrize("name", ["monte_carlo"])
def test_for_a_not_implemented_broker(name:str):
    with pytest.raises(NotImplementedError):
        BrokerFabric(name)

@pytest.mark.parametrize("name, assets", [("binance", ["BTC", "NEO"])])
def test_for_implemented_backtesting_broker(name:str, assets:list):
    broker = BrokerFabric(broker_name=name).backtesting(assets=assets)

    assert broker.__class__.__name__ == 'BackTestingBroker'
    assert broker.real_broker.__class__.__name__ == name.capitalize()
    assert broker.assets == assets
