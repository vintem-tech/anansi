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


class PostgresRelationalDb(BaseModel):
    host: str = env.str("DB_HOST", default="localhost")
    port: int = env.int("POSTGRES_PORT", default=5432)
    database: str = env.str("POSTGRES_DB", default="postgres_db")
    user: str = env.str("POSTGRES_USER", default="postgres_user")
    password: str = env.str(
        "POSTGRES_PASSWORD", default="123_postgres_password"
    )
    SQL_DEBUG:bool = False
    SQLALCHEMY_DATABASE_URL: str = "postgresql+psycopg2://{}:{}@{}:{}/{}"

    def sql_alchemy_connection_args(self):

        return dict(
            url=self.SQLALCHEMY_DATABASE_URL.format(
                self.user,
                self.password,
                self.host,
                self.port,
                self.database,
            )
        )

    def pony_connection_args(self):
        return dict(
            provider="postgres",
            user=self.user,
            password=self.password,
            host=self.host,
            database=self.database,
        )


class SqliteRelationalDb(BaseModel):
    SQL_DEBUG:bool = True  
    SQLALCHEMY_DATABASE_URL: str = "sqlite:///./anansi_sql_alchemy.db"

    def sql_alchemy_connection_args(self):
        return dict(
            url=self.SQLALCHEMY_DATABASE_URL,
            connect_args={"check_same_thread": False},
        )

    def pony_connection_args(self):
        return dict(
            provider="sqlite",
            filename="anansi_pony.sqlite",
            create_db=True,
        )


class MemorySqliteRelationalDb(BaseModel):
    SQL_DEBUG:bool = True  
    SQLALCHEMY_DATABASE_URL: str = "sqlite+pysqlite:///:memory:"

    def sql_alchemy_connection_args(self):
        return dict(
            url=self.SQLALCHEMY_DATABASE_URL,
            connect_args={"check_same_thread": False},
        )

    def pony_connection_args(self):
        return dict(provider="sqlite", filename=":memory:")


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


def get_relational_database_settings(
    provider: str,
) -> Union[PostgresRelationalDb, SqliteRelationalDb]:

    sql_provider = "{}RelationalDb".format(provider.capitalize())
    return getattr(thismodule, sql_provider)()
