from .schemas import DefaultRealTradingOperation
from .main import Operation, DefaultTrader

my_op_setup = DefaultRealTradingOperation
my_op = Operation(setup=my_op_setup)
my_trader = DefaultTrader(operation=my_op)

def run():
    my_trader.run()