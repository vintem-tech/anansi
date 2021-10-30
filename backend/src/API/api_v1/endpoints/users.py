from typing import Any, List

from fastapi import APIRouter, HTTPException
from src.utils import schemas
from src.utils.databases.sql.crud import user

endpoint = APIRouter()

@endpoint.post("/", response_model=schemas.UserReturn)
def create_user(user_in:schemas.UserCreate):
    return user.create(user_in)

@endpoint.get("/{id}", response_model=schemas.UserReturn)
def read_user_by_id(id:int):
    user_in_db = user.read_by_id(id)
    if not user_in_db:
        raise HTTPException(status_code=400, detail="User does not exist") 
    return user_in_db