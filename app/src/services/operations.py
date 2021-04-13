"""Operations management interface"""

# pylint: disable=no-member
# pylint: disable=no-name-in-module
# pylint: disable=too-few-public-methods

from typing import List

from pony.orm import commit
from pydantic import BaseModel, Json

from ..config.setups import BinanceMonitoring, OperationalSetup
from ..lib.utils.databases.sql.models import Operation
from ..lib.utils.databases.sql.schemas import Market, OperationalModes

modes = OperationalModes()


class OperationPayload(BaseModel):
    """Minimum set of attributes needed to create an operation"""

    name: str
    mode: str
    setup_: Json


def create(
    operation_payload: OperationPayload, market_list: List[Market]
) -> Operation:
    """An entrypoint to create operations"""

    operation = Operation(**operation_payload.dict())
    commit()

    if market_list:
        operation.recreate_monitors(market_list)
    return Operation[operation.id]


def create_default_backtesting(name: str) -> Operation:
    """Creates a default binance backtesting operation"""

    return create(
        operation_payload=OperationPayload(
            name=name,
            mode=modes.backtesting,
            setup_=OperationalSetup().json(),
        ),
        market_list=BinanceMonitoring().markets(),
    )
