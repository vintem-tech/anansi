from .from_broker import GetterFromBroker
from ....utils.schemas import Ticker
#from .storage import 

def klines_getter(ticker: Ticker, time_frame: str = str(), backtesting=False):
    """Instantiates a 'Getter' object, in order to get klines.

    Args:
        ticker (Ticker): Broker name and asset informations

        time_frame (str, optional): <amount><scale_unit> e.g. '1m',
        '2h'. Defaults to '' (empty string).

        backtesting (bool, optional): If True, get interpolated klines
        from time series storage. Defaults to False.

    Returns:
        [KlinesFrom]: 'FromBroker' or 'FromStorage' klines getter
    """
    #if backtesting:
    #    return FromStorage(ticker, time_frame)
    return GetterFromBroker(ticker, time_frame)
