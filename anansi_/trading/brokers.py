import sys

thismodule = sys.modules[__name__]

def get_broker(market):
    return getattr(thismodule, market.broker_name.capitalize())()

class Binance:
    fee_rate_decimal = 0.001
    minimal_amount = 0.000001