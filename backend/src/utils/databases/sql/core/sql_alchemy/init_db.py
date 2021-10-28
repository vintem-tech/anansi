from sqlalchemy.orm import Session
from src.core.config import default_system_settings
from src.utils import schemas
from src.utils.databases.sql import crud

from .base import Base  # noqa: F401
from .session import engine

# make sure all SQL Alchemy models are imported
# (src.utils.databases.sql.models) before initializing DB otherwise, SQL
# Alchemy might fail to initialize relationships properly for more
# details:
# https://github.com/tiangolo/full-stack-fastapi-postgresql/issues/28


def init_db(db: Session) -> None:
    # If you don't want to use the Alembic migrations to create tables,
    # create it un-commenting 'Base.metadata.create_all(bind=engine)'

    Base.metadata.create_all(bind=engine)

    user = crud.user.get_by_email(db, email=default_system_settings.FIRST_SUPERUSER)
    if not user:
        user_in = schemas.UserCreate(
            email=default_system_settings.FIRST_SUPERUSER,
            password=default_system_settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        user = crud.user.create(db, obj_in=user_in)  # noqa: F841
