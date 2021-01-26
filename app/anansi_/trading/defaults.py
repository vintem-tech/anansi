from ..sql_app.schemas import (
    DidiClassifierSetup,
    Market,
    OperationSetup,
    StopTrailing3T,
)


back_testing = OperationSetup(
    debbug=True,
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
    backtesting=True,
    initial_base_amount=1000.00,
    test_order=False,
    order_type="market",
    stop_is_on=True,
    allow_naked_sells=False,
)
trading_testing = OperationSetup(
    debbug=True,
    broadcasters=["PrintNotifier", "TelegramNotifier"],
    classifier_name="DidiClassifier",
    classifier_setup=DidiClassifierSetup(),
    stoploss_name="StopTrailing3T",
    stoploss_setup=StopTrailing3T(),
    market=Market(
        broker_name="Binance",
        quote_symbol="BTC",
        base_symbol="EUR",
        ticker_symbol="BTCEUR",
    ),
    backtesting=False,
    test_order=True,
    order_type="market",
    stop_is_on=False,
    allow_naked_sells=False,
)
real_trading = OperationSetup(
    debbug=True,
    broadcasters=["TelegramNotifier"],
    classifier_name="DidiClassifier",
    classifier_setup=DidiClassifierSetup(),
    stoploss_name="StopTrailing3T",
    stoploss_setup=StopTrailing3T(),
    market=Market(
        broker_name="Binance",
        quote_symbol="BTC",
        base_symbol="EUR",
        ticker_symbol="BTCEUR",
    ),
    backtesting=False,
    test_order=False,
    order_type="market",
    stop_is_on=False,
    allow_naked_sells=False,
)
