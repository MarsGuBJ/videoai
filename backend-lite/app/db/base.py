"""SQLAlchemy 声明基类与公共时间工具。"""

from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """全部 ORM 模型的声明基类。"""


def utcnow() -> datetime:
    """返回带时区的当前 UTC 时间（ORM 默认值/onupdate 使用）。"""
    return datetime.now(timezone.utc)
