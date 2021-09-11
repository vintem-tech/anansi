# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=too-few-public-methods

import requests_mock
from src.lib.brokers_wrappers.binance import Binance

broker = Binance()


def test_server_time():
    endpoint = broker.settings.time_endpoint
    server_time = {"serverTime": "1593609165616"}
    with requests_mock.mock() as m_req:
        m_req.get(endpoint, json=server_time)
        binance_time = broker.server_time()
        assert binance_time == int(1593609165616 / 1000)
