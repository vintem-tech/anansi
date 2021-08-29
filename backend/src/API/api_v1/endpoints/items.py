from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .... import get_db
from ....utils.databases.sql.crud import items as crud_items
from ....utils.schemas import item

endpoint = APIRouter()


@endpoint.get("/items/", response_model=List[item.Item])
def read_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    items = crud_items.get_items(db, skip=skip, limit=limit)
    return items
