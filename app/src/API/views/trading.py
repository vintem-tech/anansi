"""Interface between trade logic and the user"""

from pony.orm import db_session

from ...config.defaults import default_monitor_setup
from ...lib.utils.databases.sql.models import (
    LastCheck,
    Monitor,
    Operation,
    Position,
)
from ...lib.utils.databases.sql.schemas import MonitorSetup


























@db_session
def create_monitor(setup: MonitorSetup):
    Monitor(
        _setup=setup,
        position=Position(),
        last_check=LastCheck(by_classifier_at=0),
    )


@db_session
def create_default_monitor():
    create_monitor(setup=default_monitor_setup)


# Estudar na documentação do Pony como criar objetos relacionados


@db_session
def create_operation(operational_setup: OperationalSetup):
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
