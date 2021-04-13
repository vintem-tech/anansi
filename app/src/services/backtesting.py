from ..lib.marketdata.klines import ToStorage
from ..lib.utils.databases.sql.schemas import Market

def create_or_complete(market:Market, time_range:TimeRange):
    storage = ToStorage(market)
    storage.create_backtesting(since)