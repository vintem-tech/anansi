from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .... import get_db
from ....utils.databases.sql.crud import (
    items as crud_items,
    users as crud_users,
)
from ....utils.schemas import item, user

endpoint = APIRouter()


@endpoint.post("/users/", response_model=user.User)
def create_user(user_: user.UserCreate, db: Session = Depends(get_db)):
    db_user = crud_users.get_user_by_email(db, email=user_.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud_users.create_user(db=db, user_=user_)


@endpoint.get("/users/", response_model=List[user.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = crud_users.get_users(db, skip=skip, limit=limit)
    return users


@endpoint.get("/users/{user_id}", response_model=user.User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud_users.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@endpoint.post("/users/{user_id}/items/", response_model=item.Item)
def create_item_for_user(
    user_id: int, item_: item.ItemCreate, db: Session = Depends(get_db)
):
    return crud_items.create_user_item(db=db, item_=item_, user_id=user_id)
