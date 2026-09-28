"""人脸照片模块（/face/es/label/facePage）的外部 API 代理。"""

import requests
from fastapi import HTTPException

from app.core.config import get_settings

FACE_PHOTO_API_TIMEOUT_SECONDS = 30
FACE_PAGE_PATH = "/face/es/label/facePage"
SUCCESS_CODE = "0"


def query_face_page(current: int, size: int, keyword: str | None = None) -> dict:
    """分页查询人脸照片库。

    Args:
        current: 页码（从 1 开始）。
        size: 每页条数。
        keyword: 描述信息 val 模糊匹配关键字，空则不筛选。

    Returns:
        外部接口 data 部分（PageBean：total/current/size/records）。

    Raises:
        HTTPException: 服务未配置（500）、不可达（502）或业务码非成功（502）。
    """
    base_url = get_settings().face_photo_api_base_url
    if not base_url:
        raise HTTPException(status_code=500, detail="FACE_PHOTO_API_BASE_URL is not configured")
    query: dict = {}
    keyword_text = str(keyword or "").strip()
    if keyword_text:
        query["val"] = keyword_text
    try:
        response = requests.post(
            f"{base_url}{FACE_PAGE_PATH}",
            json={"current": current, "size": size, "query": query},
            timeout=FACE_PHOTO_API_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Face photo API unavailable: {exc}") from exc
    try:
        payload = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=f"Face photo API returned invalid JSON: {response.text}") from exc
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Face photo API HTTP {response.status_code}: {payload}")
    if not isinstance(payload, dict) or str(payload.get("code")) != SUCCESS_CODE:
        message = payload.get("msg") if isinstance(payload, dict) else payload
        raise HTTPException(status_code=502, detail=f"Face photo API error: {message}")
    data = payload.get("data")
    return data if isinstance(data, dict) else {}
