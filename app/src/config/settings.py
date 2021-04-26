# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument
# pylint: disable=too-few-public-methods

"""All brokers configuration must to be placed here"""

from environs import Env
from pydantic import BaseModel

env = Env()


class RelationalDatabase(BaseModel):
    provider: str
    host: str
    port: int
    database: str
    user: str
    password: str


class PostgresDatabase(RelationalDatabase):
    def __init__(self):
        super().__init__(
            provider="postgres",
            host=env.str("DB_HOST", default="localhost"),
            port=env.int("POSTGRES_PORT", default=5432),
            database=env.str("POSTGRES_DB", default="anansi_postgres"),
            user=env.str("POSTGRES_USER", default="anansi_user"),
            password=env.str("POSTGRES_PASSWORD", default="!@*_anansi_pass_123"),
        )


class InfluxDbSettings(BaseModel):
    class V1:
        credentials = dict(
            host=env.str("INFLUXDB_HOST", default="localhost"),
            port=env.int("INFLUXDB_PORT", default=8086),
            username=env.str("INFLUXDB_USER", default="Anansi"),
            password=env.str("INFLUXDB_USER_PASSWORD", default="anansi2020"),
            gzip=env.bool("INFLUXDB_GZIP", default=True),
        )

    class V2:
        credentials = dict(
            url=env.str("INFLUXDB_HOST", default="http://localhost:8086"),
            token=env.str(
                "DOCKER_INFLUXDB_INIT_ADMIN_TOKEN", default="Y7&>vj{N"
            ),
            org=env.str("DOCKER_INFLUXDB_INIT_ORG", default="anansi"),
            debug=False,
        )
        write_opts = dict(
            batch_size=1000,
            flush_interval=1000,
            jitter_interval=0,
            retry_interval=5000,
            max_retries=5,
            max_retry_delay=1000,
            exponential_base=2,
        )
        system_columns = ["result", "table", "_start", "_stop", "_measurement"]


FAKE_TELEGRAM_TOKEN = "0123456789:ABCd_F67pwokcpwjpjJKJPJoj98709IJOIp"

class TelegramSettings(BaseModel):
    token: str = env.str(
        "TELEGRAM_TOKEN",
        default=FAKE_TELEGRAM_TOKEN,
    )
    debug: int = env.int("TELEGRAM_DEBBUG_ID", default=None)
    error_id: int = env.int("TELEGRAM_ERROR_ID", default=None)
    trade_id: int = env.int("TELEGRAM_TRADE_ID", default=None)


class DefaultSettings(BaseModel):
    debug: bool = env.bool("DEBUG", default=True)
    sql_debug: bool = env.bool("SQL_DEBUG", default=False)
    relational_database: RelationalDatabase = PostgresDatabase()
    telegram: TelegramSettings = TelegramSettings()


def system_settings():
    return DefaultSettings()
