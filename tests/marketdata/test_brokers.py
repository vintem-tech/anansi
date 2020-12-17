from anansi_.marketdata.brokers import Binance
import requests_mock

def test_server_time():

    endpoint = Binance().time_endpoint
    _server_time = {"serverTime": "1593609165616"}

    with requests_mock.mock() as m:
        m.get(endpoint, json=_server_time)
        binance_time = Binance().server_time()
        assert binance_time == int(1593609165616 / 1000)