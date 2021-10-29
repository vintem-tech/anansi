from typing import Any, List

from fastapi import APIRouter
from src.utils import schemas
from src.utils.databases.sql.crud import user

endpoint = APIRouter()

@endpoint.post("/", response_model=schemas.UserReturn)
def create_user(user_in:schemas.UserCreate):
    return user.create(user_in)