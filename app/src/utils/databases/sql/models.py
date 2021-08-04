import json

import pandas as pd
from pony.orm import Database, Json, Optional, Required, Set, commit, sql_debug

from .....config.settings import system_settings
from .....config.setups import initial_wallet
from ....utils.schemas import OperationalModes, Ticker
from ...tools.serializers import Deserialize
from ..time_series_storage.models import StorageResults

settings = system_settings()
db = Database()
modes = OperationalModes()
db.bind(**settings.relational_database.dict())
sql_debug(settings.sql_debug)


class AttributeUpdater(object):
    def update(self, **kwargs):
        for attribute, value in kwargs.items():
            setattr(self, attribute, value)
            commit()


class SingleTickerMonitoring(db.Entity, AttributeUpdater):
    position = Required(Position, cascade_delete=True)
    last_check = Required(LastCheck, cascade_delete=True)
    is_active = Required(bool, default=True)
    ticker = Required(Json)
