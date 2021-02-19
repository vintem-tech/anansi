from src.domain.brokers.marketdata import Binance
from src.repositories.sql_app.schemas import Market
import requests_mock

broker = Binance(
    market=Market(
        broker_name="Binance",
        quote_symbol="BTC",
        base_symbol="USDT",
        ticker_symbol="BTCUSDT",
    )
)


def test_server_time():
    endpoint = broker.settings.time_endpoint
    _server_time = {"serverTime": "1593609165616"}
    with requests_mock.mock() as m_req:
        m_req.get(endpoint, json=_server_time)
        binance_time = broker.server_time()
        assert binance_time == int(1593609165616 / 1000)
