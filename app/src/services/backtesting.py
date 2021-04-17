from ..lib.marketdata.klines import ToStorage
from ..lib.utils.schemas import Ticker, TimeRange

def create_or_complete(ticker:Ticker, time_range:TimeRange):
    storage = ToStorage(ticker)
    storage.create_backtesting(since= time_range.since, until= time_range.until)

class BackTesting:
    pass
