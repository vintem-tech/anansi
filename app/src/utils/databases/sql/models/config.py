from pony.orm import Database, Json, Required, sql_debug

from ..models import UpdateAttributesDict
from .....config import SystemSettings

settings = SystemSettings()

db_adapter = settings.relational_database_adapter
db = Database()
db.bind(**db_adapter.dict())
sql_debug(settings.sql_debug)


class Messages(db.Entity, UpdateAttributesDict):
    notifier_headers = Required(Json)
    trading_monitor = Required(Json)

class Preferences(db.Entity, UpdateAttributesDict):
    date_time = Required(Json)
    back_testing = Required(Json)
    notifier = Required(Json)
    trading = Required(Json)

db.generate_mapping(create_tables=True)
