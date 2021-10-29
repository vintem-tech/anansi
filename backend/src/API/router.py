from fastapi import APIRouter

from .api_v1.endpoints import users

api = APIRouter()

api.include_router(users.endpoint, prefix="/users")
