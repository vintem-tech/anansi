# pylint: disable=unused-wildcard-import, method-hidden
# pylint: disable=wildcard-import

"""Some defaults parameters"""

import sys

from ..sql_app.schemas import *

thismodule = sys.modules[__name__]
broadcasters = Broadcasters()

default_didi_index_setup = DidiIndexSetup(
    price_metrics="ohlc4", number_samples=(3, 20, 80)
)
default_bollinger_bands_setup = BollingerBandsSetup(
    price_metrics="ohlc4", number_samples=20, number_STDs=2.0
)
default_didi_classifier_setup = DidiClassifierSetup(
    didi_index=default_didi_index_setup,
    bollinger_bands=default_bollinger_bands_setup,
    partial_opened_bands_weight=1.0,
    time_frame="6h",
)
default_classifier = Classifier(
    name="DidiClassifier", setup=default_didi_classifier_setup
)
default_stoploss_setup = StopTrailing3T(
    time_frame="1m",
    price_metric="oc2",
    first_trigger=Trigger(
        rate=5, treshold=Treshold(m_found=6, n_datapoints=10)
    ),
    second_trigger=Trigger(
        rate=3.5, treshold=Treshold(m_found=15, n_datapoints=30)
    ),
    third_trigger=Trigger(
        rate=1.0, treshold=Treshold(m_found=80, n_datapoints=120)
    ),
    update_target_if=Trigger(
        rate=0.5, treshold=Treshold(m_found=7, n_datapoints=10)
    ),
)
default_stop_loss = StopLoss(
    is_on=True,
    name="StopTrailing3T",
    setup=default_stoploss_setup,
)
default_notifier = Notifier(
    debug=True, broadcasters=[broadcasters.print_on_screen]
)
default_backtesting = BackTesting(
    is_on=True,
    price_metrics="ohlc4",
    fee_rate_decimal=0.001,
    initial_portfolio=Portfolio(quote=0.0, base=1000.0),
)
default_market = Market(
    broker_name="Binance",
    quote_symbol="BTC",
    base_symbol="EUR",
    ticker_symbol="BTCEUR",
)
default_operational_setup = OperationalSetup(
    classifier=default_classifier,
    stoploss=default_stop_loss,
    notifier=default_notifier,
    backtesting=default_backtesting,
    market=default_market,
    default_order_type="market",
    allow_naked_sells=False,
)

default_backtesting_operational_setup = default_operational_setup
default_real_trading_setup = default_operational_setup
default_test_trading_setup = default_operational_setup


def get_operational_setup_for(operation_mode: str) -> OperationalSetup:
    """Returns the desired operational_setup given an operation_mode"""
    return getattr(
        thismodule, "default_{}_operational_setup".format(operation_mode)
    ).json()
