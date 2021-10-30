from src.utils.databases.sql.core.pony import db

from .trading import Trader
from .users import User

db.generate_mapping(create_tables=True)
