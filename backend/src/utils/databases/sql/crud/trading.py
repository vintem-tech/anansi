from src.utils.databases.sql.core.pony import db_session, safety_commit
from src.utils.databases.sql.models.trading import Trader
from src.utils.databases.sql.models.users import User
from src.utils.schemas import TraderCreate, TraderReturn


class CrudTrader:
    def create_by_owner(self, trader_create:TraderCreate, owner: User):
        with db_session:
            trader = Trader(**trader_create, owner=owner)
            safety_commit()
        
        trader_return = trader.to_dict()
        return TraderReturn(**trader_return)

    def create_by_owner_id(self):
        pass

    def create_by_owner_email(self):
        pass

trader = CrudTrader()