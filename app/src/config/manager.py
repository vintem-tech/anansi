# pylint:disable=missing-module-docstring
# pylint:disable=missing-function-docstring
# pylint:disable=missing-class-docstring
# pylint:disable=too-few-public-methods
# pylint:disable=no-name-in-module

#from typing import List

import pendulum
from environs import Env
from pydantic import BaseModel

from ..utils.schemas import Broadcasters, Wallet
from .database_adapters import InfluxDbSettings, get_relational_database

initial_wallet: Wallet = dict(USDT=1000.00)  # Backtesting scenarios
broadcasters = Broadcasters()

env = Env()

from ..utils.databases.sql.crud import user


class SystemSettings(BaseModel):  # Non editable
    class Config:
        arbitrary_types_allowed = True

    avaliable_timezones: list = list(pendulum.timezones)
    sql_debug: bool = env.bool("SQL_DEBBUG", default=False)
    relational_database: BaseModel = get_relational_database(
        provider=env.str("RELATIONAL_DATABASE_PROVIDER", default="sqlite")
    )
    time_series_storage: BaseModel = InfluxDbSettings
    API_prefix_version: str = env.str("API_PREFIX_VERSION", default="/api/v1")
