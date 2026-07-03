import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _build_database_url() -> str:
    explicit = os.environ.get("VIDEOAI_DATABASE_URL")
    if explicit:
        return explicit
    host = os.environ.get("POSTGRES_HOST", "postgres")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "videoai")
    password = os.environ.get("POSTGRES_PASSWORD", "videoai")
    db = os.environ.get("POSTGRES_DB", "videoai")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


DATABASE_URL = _build_database_url()

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
