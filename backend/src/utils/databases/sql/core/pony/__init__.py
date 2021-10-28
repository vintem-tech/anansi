from src.core.config import default_system_settings
from src.log import logger

from pony.orm import (
    CommitException,
    Database,
    Json,
    Optional,
    Required,
    RollbackException,
    Set,
    commit,
    db_session,
    rollback,
    sql_debug,
)

db_adapter = default_system_settings.relational_database_adapter
db = Database()
db.bind(**db_adapter.pony_connection_args())
sql_debug(db_adapter.SQL_DEBUG)


def safety_commit(max_attempts=15):
    for attempt in range(0, max_attempts):
        try:
            commit()
            return
        except (CommitException, Exception) as error:
            logger.exception(error)
            try:
                rollback()
                continue
            except (RollbackException, Exception) as error:
                logger.exception(error)
                raise Exception(error)


class Base(db.Entity):
    def update_attributes_dict(self, **kwargs):
        for attribute, value in kwargs.items():
            setattr(self, attribute, value)
            safety_commit()
