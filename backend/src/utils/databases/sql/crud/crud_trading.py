from typing import List

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from src.utils.databases.sql.crud.base import CRUDBase
from src.utils.databases.sql.models.trading import Trader
from src.utils.schemas.trading import TraderCreate, TraderUpdate


class CRUDTrader(CRUDBase[Trader, TraderCreate, TraderUpdate]):
    def create_with_owner(
        self, db: Session, *, obj_in: TraderCreate, owner_id: int
    ) -> Trader:
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data, owner_id=owner_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_multi_by_owner(
        self, db: Session, *, owner_id: int, skip: int = 0, limit: int = 100
    ) -> List[Trader]:
        return (
            db.query(self.model)
            .filter(Trader.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
            .all()
        )


trader = CRUDTrader(Trader)
