# pylint:disable=no-name-in-module
# pylint:disable=missing-module-docstring
# pylint:disable=missing-class-docstring
# pylint:disable=too-few-public-methods

from typing import Optional

from pydantic import BaseModel, EmailStr

from src.utils.schemas.notifiers import TelegramChatsIds

# Shared properties
class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    is_superuser: bool = False
    full_name: Optional[str] = str()
    telegram_chats_ids:TelegramChatsIds = TelegramChatsIds()


# Makes email and password required (receive via API on creation)
class UserCreate(UserBase):
    email: EmailStr
    password: str

# Properties to receive via API on update
class UserUpdate(UserBase):
    password: Optional[str] = str()


# Properties to return via API
class UserReturn(UserBase):
    id: int
