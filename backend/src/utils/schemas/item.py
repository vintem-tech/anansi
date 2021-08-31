# pylint:disable=no-name-in-module
# pylint:disable=missing-module-docstring
# pylint:disable=missing-class-docstring
# pylint:disable=too-few-public-methods

from typing import Optional

from pydantic import BaseModel


class ItemBase(BaseModel):
    title: str
    description: Optional[str] = None


class ItemCreate(ItemBase):
    pass


class Item(ItemBase):
    id: int
    owner_id: int

    class Config:
        orm_mode = True
