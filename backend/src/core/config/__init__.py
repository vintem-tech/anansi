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

    SECRET_KEY: str = env.str(
        "SECRET_KEY",
        default="ca809d720daa1acc6e63d8f58bfd4006bd8f6614c272543c17ec1598f90b2158",
    )
    FIRST_SUPERUSER: str = env.str(
        "FIRST_SUPERUSER", default="anansi@email.com"
    )
    FIRST_SUPERUSER_PASSWORD: str = env.str(
        "FIRST_SUPERUSER_PASSWORD", default="12345"
    )
    TELEGRAM_BOT_TOKEN: str = env.str(
        "TELEGRAM_BOT_TOKEN",
        default="0123456789:ageRPkvuPXBcChgrZSnz9rF9W23Gv7hthuT",
    )
    USERS_OPEN_REGISTRATION: bool = False
    ACCESS_TOKEN_EXPIRE_MINUTES: int = env.int(
        "ACCESS_TOKEN_EXPIRE_MINUTES", default=120
    )
    date_time = DateTimeSettings()
    sql_debug: bool = env.bool("SQL_DEBBUG", default=False)
    relational_database_adapter: BaseModel = get_relational_database_settings(
        provider=env.str("RELATIONAL_DATABASE_PROVIDER", default="sqlite")
    )
    time_series_storage: BaseModel = InfluxDbSettings()
    API_PREFIX_VERSION: str = env.str("API_PREFIX_VERSION", default="/api/v1")


settings = SystemSettings()
