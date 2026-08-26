"""数据库引擎与会话工厂。"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

DATABASE_URL = get_settings().database_url

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI Depends 用会话提供者：请求结束自动关闭。

    Yields:
        绑定到全局 engine 的 SQLAlchemy Session。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
