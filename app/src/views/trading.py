from pony.orm import db_session
from ..config.defaults import get_operational_setup_for
from .models import Position, Operation, LastCheck

@db_session
def create_default_operation(operation_mode: str):
    Operation(
        json_setup=get_operational_setup_for(operation_mode),
        position=Position(),
        last_check=LastCheck(by_classifier_at=0),
    )
