# pylint:disable=missing-module-docstring
# pylint:disable=missing-function-docstring
# pylint:disable=missing-class-docstring
# pylint:disable=too-few-public-methods
# pylint:disable=no-name-in-module

import sys
from typing import Union

from environs import Env
from pydantic import BaseModel

thismodule = sys.modules[__name__]
env = Env()


class PostgresDatabase(BaseModel):
    provider: str = "postgres"
    host: str = env.str("DB_HOST", default="localhost")
    port: int = env.int("POSTGRES_PORT", default=5432)
    database: str = env.str("POSTGRES_DB", default="postgres_db")
    user: str = env.str("POSTGRES_USER", default="postgres_user")
    password: str = env.str(
        "POSTGRES_PASSWORD", default="123_postgres_password"
    )


class SqliteDatabase(BaseModel):
    provider: str = "sqlite"
    filename: str = "database.sqlite"
    create_db: bool = True


class MemorySqliteDatabase(BaseModel):
    provider: str = "sqlite"
    filename: str = ":memory:"


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


def get_relational_database(
    provider: str,
) -> Union[PostgresDatabase, SqliteDatabase]:

    return getattr(thismodule, "{}Database".format(provider.capitalize()))()
