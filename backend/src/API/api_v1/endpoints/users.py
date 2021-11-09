from fastapi import APIRouter, Body, Depends, HTTPException
from src.utils import schemas
from src.utils.databases.sql.crud import user
from typing import Any
from src.API import deps

endpoint = APIRouter()


@endpoint.post("/", response_model=schemas.UserReturn)
def create_user(
    user_in: schemas.UserCreate,
    current_user: schemas.UserReturn = Depends(
        deps.get_current_active_superuser
    ),
) -> Any:
    user_in_db = user.read_by_email(email=user_in.email)
    if user_in_db:
        raise HTTPException(
            status_code=400,
            detail="Email already in use. Login or try a different one.",
        )
    return user.create(user_in)


@endpoint.get("/{id}", response_model=schemas.UserReturn)
def read_user_by_id(id: int):
    user_in_db = user.read_by_id(id)
    if not user_in_db:
        raise HTTPException(status_code=400, detail="User does not exist")
    return user_in_db
