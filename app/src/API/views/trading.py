# pylint: disable=no-member
"""Interface between trade logic and the user"""

from pony.orm import commit

from ...config.setups import (
    BackTesting,
    Notifier,
    OperationalSetup,
    BinanceMonitoring,
)
from ...lib.utils.databases.sql.models import Operation
from ...lib.utils.databases.sql.schemas import OperationalModes

modes = OperationalModes()


def create_operation_with_monitors(
    operation_name: str, mode, setup, notifier, market_list, **kwargs
) -> Operation:

    payload = dict(
        name=operation_name,
        mode=mode,
        _setup=setup.json(),
        _notifier=notifier.json(),
    )

    if mode == modes.backtesting:
        backtesting = kwargs.get("backtesting")
        if not backtesting:
            raise KeyError("Backtesting must be passed on backtesting mode")

        payload = dict(**payload, _backtesting=backtesting.json())

    operation = Operation(**payload)
    commit()

    operation.create_monitors(market_list)
    return Operation[operation.id]


def create_default_operation_with_monitors(name: str) -> Operation:
    return create_operation_with_monitors(
        operation_name=name,
        mode=modes.backtesting,
        setup=OperationalSetup(),
        notifier=Notifier(),
        market_list=BinanceMonitoring().markets(),
        backtesting=BackTesting(),
    )
