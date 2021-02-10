"""Some defaults parameters"""

from ..sql_app.schemas import (
    BackTesting,
    DidiClassifierSetup,
    Market,
    OperationalSetup,
    StopTrailing3T,
    Order,
)

back_testing = OperationalSetup(
    debbug=True,
    backtesting = BackTesting(is_on=True),
    broadcasters=["PrintNotifier"],
    classifier_name="DidiClassifier",
    classifier_setup=DidiClassifierSetup(),
    stoploss_name="StopTrailing3T",
    stoploss_setup=StopTrailing3T(),
    market=Market(
        broker_name="Binance",
        quote_symbol="BTC",
        base_symbol="USDT",
        ticker_symbol="BTCUSDT",
    ),
    default_order = Order(
        notify=True,
        order_type="market",
    ),
    stop_is_on=True,
    allow_naked_sells=False,
)