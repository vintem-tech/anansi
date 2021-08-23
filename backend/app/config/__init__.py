# pylint:disable=missing-module-docstring
# pylint:disable=missing-function-docstring
# pylint:disable=missing-class-docstring
# pylint:disable=too-few-public-methods
# pylint:disable=no-name-in-module


import pendulum
from environs import Env
from pydantic import BaseModel

from .databases import InfluxDbSettings, get_relational_database_settings

env = Env()


class DateTimeSettings(BaseModel):
    avaliable_timezones: list = list(pendulum.timezones)
    system_timezone: str = "UTC"
    timestamp_unit: str = "s"
    human_readable_format: str = "YYYY-MM-DD HH:mm:ss"


class SystemSettings(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    date_time = DateTimeSettings()
    sql_debug: bool = env.bool("SQL_DEBBUG", default=False)
    relational_database_adapter: BaseModel = get_relational_database_settings(
        provider=env.str("RELATIONAL_DATABASE_PROVIDER", default="sqlite")
    )
    time_series_storage: BaseModel = InfluxDbSettings()
    API_prefix_version: str = env.str("API_PREFIX_VERSION", default="/api/v1")
