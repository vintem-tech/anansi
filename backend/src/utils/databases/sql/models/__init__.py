from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .....config import SystemSettings

from urllib.parse import urlparse

sql_adapter = SystemSettings().relational_database_adapter

#SQLALCHEMY_DATABASE_URL = "postgresql://user:password@postgresserver/db"

SQLALCHEMY_DATABASE_URL = "postgresql://{}:{}@{}:{}/{}"
db_url = SQLALCHEMY_DATABASE_URL.format("anansi_user", "!*_anansi_pass_123", "postgres", 5432, "anansi_postgres")

#engine = create_engine(**sql_adapter.connection_args())
engine = create_engine(url=db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
