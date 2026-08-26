"""MinIO 视频智能分析服务的外部 API 代理。"""

from typing import Any

import requests
from fastapi import HTTPException

from app.core.config import get_settings
from app.services.person_search import parse_person_api_response

VIDEO_ANALYSIS_API_TIMEOUT_SECONDS = 600


def video_analysis_api_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST 调用 MinIO 视频智能分析服务。

    Args:
        path: API 路径。
        payload: JSON 请求体。

    Returns:
        解析后的响应 JSON。

    Raises:
        HTTPException: 服务未配置（500）、不可达（502）或返回非 2xx。
    """
    base_url = get_settings().video_analysis_api_base_url
    if not base_url:
        raise HTTPException(status_code=500, detail="VIDEO_ANALYSIS_API_BASE_URL is not configured")
    try:
        response = requests.post(f"{base_url}{path}", json=payload, timeout=VIDEO_ANALYSIS_API_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Video analysis API unavailable: {exc}") from exc
    return parse_person_api_response(response)
