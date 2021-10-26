# pylint:disable=missing-module-docstring
# pylint:disable=missing-class-docstring
# pylint:disable=too-few-public-methods


from typing import TYPE_CHECKING

from sqlalchemy import JSON, Column, ForeignKey, Integer, PickleType, String
from sqlalchemy.orm import relationship
from src.utils.databases.sql.core.base_class import Base

if TYPE_CHECKING:
    from .user import User  # noqa: F401


class Trader(Base):
    id = Column(Integer, primary_key=True, index=True)
    broker = Column(String, index=True)
    tickers = Column(PickleType)
    mode = Column(String)
    classifier = Column(String)
    classifier_setup = Column(JSON)
    owner_id = Column(Integer, ForeignKey("user.id"))
    owner = relationship("User", back_populates="traders")
