from src.utils.databases.sql.core.pony import Base, Required, Json, Optional
from .users import User

class Trader(Base):
    owner = Required(User) # foreing key
    broker = Required(str)
    tickers = Required(Json)
    mode = Required(str)
    classifier = Optional(str)
    classifier_setup = Optional(Json)
