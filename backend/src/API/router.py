from fastapi import APIRouter

from .api_v1.endpoints import items, users

api = APIRouter()

api.include_router(items.endpoint, prefix="/items")
api.include_router(users.endpoint, prefix="/users")
