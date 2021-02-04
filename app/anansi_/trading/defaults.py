from ..sql_app.schemas import (
    BackTesting,
    DidiClassifierSetup,
    Market,
    OperationSetup,
    StopTrailing3T,
    Order,
)


back_testing = OperationSetup(
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
        test_order=False,
        notify=True,
        order_type="market",
    ),
    stop_is_on=True,
    allow_naked_sells=False,
)
#TODO: Correção daqui pra baixo:
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
