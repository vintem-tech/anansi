
# Import all the models, so that Base has them before being
# imported by Alembic
from src.utils.databases.sql.models.item import Item # noqa
from src.utils.databases.sql.models.user import User # noqa

from .base_class import Base  # noqa
