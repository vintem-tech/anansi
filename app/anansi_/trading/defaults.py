from ..sql_app.schemas import Market, OpSetup

back_testing = OpSetup()

trading_testing = OpSetup(
    debbug=True,
    broadcasters=["PrintNotifier", "TelegramNotifier"],
    market=Market(
        broker_name="Binance", quote_symbol="BTC", base_symbol="EUR"
    ),
    time_frame="6h",
    backtesting=False,
    test_order=True,
)

real_trading = OpSetup(
    debbug=True,
    broadcasters=["TelegramNotifier"],
    market=Market(
        broker_name="Binance", quote_symbol="BTC", base_symbol="EUR"
    ),
    time_frame="6h",
    backtesting=False,
    test_order=False,
)
