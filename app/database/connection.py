import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database.models import Base

load_dotenv()


def get_database_url() -> str:
    host = os.environ.get("FOOTBALLBOT_DB_HOST", "localhost")
    port = os.environ.get("FOOTBALLBOT_DB_PORT", "5433")
    name = os.environ.get("FOOTBALLBOT_DB_NAME", "footballbot")
    user = os.environ.get("FOOTBALLBOT_DB_USER", "postgres")
    password = os.environ.get("FOOTBALLBOT_DB_PASSWORD", "postgres")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


def get_async_database_url() -> str:
    host = os.environ.get("FOOTBALLBOT_DB_HOST", "localhost")
    port = os.environ.get("FOOTBALLBOT_DB_PORT", "5433")
    name = os.environ.get("FOOTBALLBOT_DB_NAME", "footballbot")
    user = os.environ.get("FOOTBALLBOT_DB_USER", "postgres")
    password = os.environ.get("FOOTBALLBOT_DB_PASSWORD", "postgres")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"


def create_tables():
    """Create tables using sync engine (needed because async engine can't run DDL inline)."""
    engine = create_engine(get_database_url())
    Base.metadata.create_all(engine)
    engine.dispose()


def create_async_db_engine():
    return create_async_engine(get_async_database_url())


def create_async_session_factory(engine):
    return sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
