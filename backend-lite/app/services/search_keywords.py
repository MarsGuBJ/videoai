"""搜索关键词记录：内存态、数据库持久化与统计聚合。

文搜视频（video-analysis 的 prompt）与文搜图（text-search 的 message）
在查询时各写入一条记录；内存态（state.search_keywords_store）为 API 真源，
数据库写入与其它模块一致采用尽力持久化（失败仅记录日志）。
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, cast

from sqlalchemy import Table
from sqlalchemy.exc import SQLAlchemyError

from app import state
from app.db.session import SessionLocal, engine
from app.models.search_keyword import SearchKeywordORM
from app.schemas.search_keyword import SearchKeywordOut, SearchKeywordStatItem

logger = logging.getLogger(__name__)

SEARCH_TYPE_TEXT_VIDEO = "text_video"
SEARCH_TYPE_TEXT_IMAGE = "text_image"
VALID_SEARCH_TYPES = (SEARCH_TYPE_TEXT_VIDEO, SEARCH_TYPE_TEXT_IMAGE)

DEFAULT_LIST_LIMIT = 50
MAX_LIST_LIMIT = 200
DEFAULT_STATS_LIMIT = 20
MAX_STATS_LIMIT = 100


def search_keyword_out(record: dict[str, Any]) -> SearchKeywordOut:
    """把内存态记录字典转为对外 DTO。

    Args:
        record: 内存态记录字典。

    Returns:
        camelCase 对外 DTO。
    """
    return SearchKeywordOut(
        id=str(record["id"]),
        keyword=str(record["keyword"]),
        searchType=str(record["search_type"]),
        createdAt=record["created_at"],
    )


def record_search_keyword(keyword: str, search_type: str) -> dict[str, Any] | None:
    """记录一次关键词查询：写入内存态并尽力持久化。

    Args:
        keyword: 用户输入的关键词（去除首尾空白后非空才记录）。
        search_type: 搜索类型（text_video / text_image）。

    Returns:
        写入的记录字典；关键词为空或类型非法时返回 None。
    """
    text = keyword.strip()
    if not text or search_type not in VALID_SEARCH_TYPES:
        return None
    record: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "keyword": text[:500],
        "search_type": search_type,
        "created_at": datetime.now(timezone.utc),
    }
    state.search_keywords_store.append(record)
    persist_search_keyword(record)
    return record


def list_search_keywords(limit: int = DEFAULT_LIST_LIMIT) -> list[SearchKeywordOut]:
    """按时间倒序返回最近的关键词记录。

    Args:
        limit: 返回条数上限。

    Returns:
        关键词记录列表（最新在前）。
    """
    records = state.search_keywords_store[-limit:]
    return [search_keyword_out(item) for item in reversed(records)]


def search_keyword_stats(
    search_type: str | None = None, limit: int = DEFAULT_STATS_LIMIT
) -> list[SearchKeywordStatItem]:
    """按关键词聚合查询次数，次数相同则按最近查询时间倒序。

    Args:
        search_type: 可选，按搜索类型过滤。
        limit: 返回条数上限。

    Returns:
        关键词统计列表（count 降序）。
    """
    buckets: dict[tuple[str, str], dict[str, Any]] = {}
    for record in state.search_keywords_store:
        if search_type and record["search_type"] != search_type:
            continue
        key = (record["keyword"], record["search_type"])
        bucket = buckets.get(key)
        if bucket is None:
            bucket = {"count": 0, "last_searched_at": record["created_at"]}
            buckets[key] = bucket
        bucket["count"] += 1
        if record["created_at"] > bucket["last_searched_at"]:
            bucket["last_searched_at"] = record["created_at"]
    ranked = sorted(buckets.items(), key=lambda item: (-item[1]["count"], -item[1]["last_searched_at"].timestamp()))
    return [
        SearchKeywordStatItem(
            keyword=keyword,
            searchType=stype,
            count=bucket["count"],
            lastSearchedAt=bucket["last_searched_at"],
        )
        for (keyword, stype), bucket in ranked[:limit]
    ]


def ensure_search_keyword_schema() -> None:
    """轻量迁移：确保 search_keywords 表存在（幂等，容错不阻断启动）。"""
    try:
        with engine.begin() as conn:
            cast(Table, SearchKeywordORM.__table__).create(conn, checkfirst=True)
    except SQLAlchemyError as exc:  # 数据库不可达时跳过迁移，不阻断启动
        logger.error("search keyword schema ensure failed: %s", exc)


def load_search_keywords_from_db() -> None:
    """启动时把数据库中的关键词记录载入内存存储。"""
    try:
        with SessionLocal() as pgdb:
            rows = pgdb.query(SearchKeywordORM).order_by(SearchKeywordORM.created_at).all()
            state.search_keywords_store.clear()
            for row in rows:
                state.search_keywords_store.append(
                    {
                        "id": str(row.id),
                        "keyword": row.keyword,
                        "search_type": row.search_type,
                        "created_at": row.created_at,
                    }
                )
    except SQLAlchemyError as exc:  # 数据库不可达时以空记录集启动（与其它模块一致）
        logger.error("search keyword load failed: %s", exc)


def persist_search_keyword(record: dict[str, Any]) -> None:
    """把记录写入数据库；失败仅记录日志，不影响内存态。

    Args:
        record: 待持久化的记录字典。
    """
    try:
        with SessionLocal() as pgdb:
            pgdb.add(
                SearchKeywordORM(
                    id=str(record["id"]),
                    keyword=str(record["keyword"]),
                    search_type=str(record["search_type"]),
                    created_at=record["created_at"],
                )
            )
            pgdb.commit()
    except SQLAlchemyError as exc:
        logger.error("search keyword persist failed: %s", exc)
