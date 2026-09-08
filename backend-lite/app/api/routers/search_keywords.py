"""搜索关键词查询路由：最近记录列表与关键词统计。"""

from fastapi import APIRouter, Query

from app.schemas.search_keyword import SearchKeywordOut, SearchKeywordStatItem
from app.services.search_keywords import (
    DEFAULT_LIST_LIMIT,
    DEFAULT_STATS_LIMIT,
    MAX_LIST_LIMIT,
    MAX_STATS_LIMIT,
    list_search_keywords,
    search_keyword_stats,
)

router = APIRouter()


@router.get("/api/search-keywords", response_model=list[SearchKeywordOut])
def list_keywords(
    limit: int = Query(DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT),
) -> list[SearchKeywordOut]:
    """按时间倒序返回最近的关键词查询记录。"""
    return list_search_keywords(limit)


@router.get("/api/search-keywords/stats", response_model=list[SearchKeywordStatItem])
def keyword_stats(
    searchType: str | None = Query(None),  # noqa: N803  # 对外契约 camelCase 查询参数
    limit: int = Query(DEFAULT_STATS_LIMIT, ge=1, le=MAX_STATS_LIMIT),
) -> list[SearchKeywordStatItem]:
    """按关键词聚合查询次数（可按搜索类型过滤）。"""
    return search_keyword_stats(search_type=searchType, limit=limit)
