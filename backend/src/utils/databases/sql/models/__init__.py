#from .item import Item
from .users import User
from .trading import Trader
from src.utils.databases.sql.core.pony import db

db.generate_mapping(create_tables=True)