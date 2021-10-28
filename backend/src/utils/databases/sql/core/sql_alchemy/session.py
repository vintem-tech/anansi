
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.core.config import default_system_settings

sql_adapter = default_system_settings.relational_database_adapter

#engine = create_engine(settings.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)

engine = create_engine(**sql_adapter.connection_args(), pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)