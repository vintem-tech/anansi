# pylint:disable=no-name-in-module
# pylint:disable=missing-module-docstring
# pylint:disable=missing-class-docstring
# pylint:disable=too-few-public-methods

from typing import Optional

from pydantic import BaseModel, EmailStr

from src.utils.schemas.notifiers import TelegramChatsIds

class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    is_superuser: bool = False
    full_name: Optional[str] = None
    telegram_chats_ids:TelegramChatsIds = TelegramChatsIds()

class UserCreate(UserBase):
    email: EmailStr
    password: str