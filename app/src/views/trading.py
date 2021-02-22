"""Interface between trade logic and the user"""

from pony.orm import db_session
from .defaults import get_operational_setup_for
from ..repositories.sql_app.models import Position, Operation, LastCheck
from ..repositories.sql_app.schemas import OperationalSetup

@db_session
def create_operation(operational_setup:OperationalSetup):
    """Given an operational setup, creates an operation"""

    Operation(
        json_setup=operational_setup,
        position=Position(),
        last_check=LastCheck(by_classifier_at=0),
    )

@db_session
def create_default_operation(operation_mode: str):
    """Given an operation mode ('backtesting', 'real_trading' or
    'test_trading'), creates an operation"""

    setup = get_operational_setup_for(operation_mode)
    create_operation(setup)
