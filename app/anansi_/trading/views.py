from pony.orm import db_session
from . import defaults
from .models import Position, Operation, TradeLog, LastCheck

@db_session
def create_default_operation(operation_mode: str):
    Operation(
        setup=getattr(defaults, operation_mode).json(),
        position=Position(),
        last_check=LastCheck(by_classifier_at=0),
    )
