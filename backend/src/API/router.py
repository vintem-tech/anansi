from fastapi import APIRouter

from .api_v1.endpoints import users, trading

api = APIRouter()

api.include_router(users.endpoint, prefix="/users")
api.include_router(trading.endpoint, prefix='/trading')
