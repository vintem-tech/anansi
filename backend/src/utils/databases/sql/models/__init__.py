from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .....config import SystemSettings

sql_adapter = SystemSettings().relational_database_adapter

engine = create_engine(**sql_adapter.connection_args())
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
