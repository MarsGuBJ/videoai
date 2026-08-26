"""兼容壳：实现已拆至 app/db/，此处仅 re-export。"""

from app.db.base import Base
from app.db.session import DATABASE_URL, SessionLocal, engine, get_db

__all__ = ["DATABASE_URL", "Base", "SessionLocal", "engine", "get_db"]
