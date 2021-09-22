# pylint:disable=no-name-in-module
# pylint:disable=missing-module-docstring
# pylint:disable=missing-function-docstring
# pylint:disable=invalid-name

from sqlalchemy.orm import Session

from ....schemas import item
from ..models import items


def get_items(db: Session, skip: int = 0, limit: int = 100):
    return db.query(items.Item).offset(skip).limit(limit).all()


def create_user_item(db: Session, item_: item.ItemCreate, user_id: int):
    db_item = items.Item(**item_.dict(), owner_id=user_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item
