from src.utils.databases.sql.core.pony import Base, Required, Json
from .users import User

class Trader(Base):
    owner = Required(User) # foreing key
    broker = Required(str)
    tickers = Required(Json)
    mode = Required(str)
    classifier = Required(str)
    classifier_setup = Required(Json)
