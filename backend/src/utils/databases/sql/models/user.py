# pylint:disable=missing-module-docstring
# pylint:disable=missing-class-docstring
# pylint:disable=too-few-public-methods


from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, Integer, String, PickleType
from sqlalchemy.orm import relationship
from src.utils.databases.sql.core.base_class import Base

if TYPE_CHECKING:
    from .item import Item  # noqa: F401
    from .trading import Trader


class User(Base):
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)
    items = relationship("Item", back_populates="owner")
    traders = relationship("Trader", back_populates="owner")
    telegram_chats_ids = Column(PickleType)
