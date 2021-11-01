from pydantic import EmailStr
from src.utils.databases.sql.core.pony import db_session, safety_commit
from src.utils.databases.sql.models.trading import Trader
from src.utils.databases.sql.models.users import User
from src.utils.schemas import TraderCreate, TraderReturn, modes


class CrudTrader:
    def create_by_owner(self, trader_create: TraderCreate, owner: User):
        with db_session:
            trader = Trader(**trader_create.dict(), owner=owner)
            safety_commit()
            trader_return = trader.to_dict()

        return TraderReturn(**trader_return)

    def create_by_owner_id(self, trader_create: TraderCreate, id=int):
        with db_session:
            user_return = User.get(id=id)
            return self.create_by_owner(trader_create, user_return)

    def create_by_owner_email(
        self, trader_create: TraderCreate, email: EmailStr
    ):
        with db_session:
            user_return = User.get(email=email)
            return self.create_by_owner(trader_create, user_return)

    def read_real_traders(self):
        traders = Trader.select().filter(lambda t: t.mode == modes.real)
        return [TraderReturn(**trader.to_dict()) for trader in traders]


trader = CrudTrader()
