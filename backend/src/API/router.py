from fastapi import APIRouter

from .api_v1.endpoints import login, trading, users

api = APIRouter()

api.include_router(users.endpoint, prefix="/users")
api.include_router(trading.endpoint, prefix="/trading")
api.include_router(login.endpoint, prefix="/login")
