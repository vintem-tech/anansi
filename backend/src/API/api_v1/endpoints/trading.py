from fastapi import APIRouter, HTTPException
from pydantic import EmailStr
from src.utils import schemas
from src.utils.databases.sql.crud import trader

endpoint = APIRouter()


@endpoint.post("/{id}", response_model=schemas.TraderReturn)
def create_trader_by_user_id(trader_in: schemas.TraderCreate, id: int):
    return trader.create_by_owner_id(trader_in, id)
