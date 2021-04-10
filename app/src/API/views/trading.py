# pylint: disable=no-member
"""Interface between trade logic and the user"""

from typing import List

from pony.orm import commit

from ...config.setups import BinanceMonitoring, OperationalSetup
from ...lib.utils.databases.sql.models import Operation
from ...lib.utils.databases.sql.schemas import Market, OperationalModes

modes = OperationalModes()


def create_operation_with_monitors(
    operation_name: str,
    mode: str,
    setup: OperationalSetup,
    market_list: List[Market],
    **kwargs
) -> Operation:

    payload = dict(
        name=operation_name,
        mode=mode,
        _setup=setup.json(),
    )

    operation = Operation(**payload)
    commit()

    operation.recreate_monitors(market_list)
    return Operation[operation.id]


def create_default_operation_with_monitors(name: str) -> Operation:
    return create_operation_with_monitors(
        operation_name=name,
        mode=modes.backtesting,
        setup=OperationalSetup(),
        market_list=BinanceMonitoring().markets(),
    )
