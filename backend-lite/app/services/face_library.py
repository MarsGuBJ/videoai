"""人脸照片模块（/face/es/label/facePage）的外部 API 代理。"""

import requests
from fastapi import HTTPException

from app.core.config import get_settings

FACE_PHOTO_API_TIMEOUT_SECONDS = 30
FACE_PAGE_PATH = "/face/es/label/facePage"
# 现网人脸照片模块成功码为 "00000"，早期对接口径为 "0"，故按数值 0 判定而不是比对字面量


def _is_success_code(code: object) -> bool:
    """判断外部接口业务码是否成功（兼容 "0" / "00" / "00000"）。

    Args:
        code: 外部接口返回的 code 字段。

    Returns:
        业务码数值为 0 返回 True，非数字或非零返回 False。
    """
    try:
        return int(str(code).strip()) == 0
    except ValueError:
        return False


def _absolutize_record_urls(data: dict, image_base_url: str) -> dict:
    """把记录里相对的图片路径补全为绝对 URL。

    外部接口返回的是 MinIO 对象路径（形如 ``/minio/city/...``），前端直接当作 img.src
    使用会被解析到本平台域名下而拿不到图片；这里按配置的图片基址补全。

    Args:
        data: 外部接口的 data（含 records）。
        image_base_url: 图片服务基址（如 http://113.249.91.53:9000），为空则不处理。

    Returns:
        就地补全后的 data。
    """
    base = str(image_base_url or "").rstrip("/")
    records = data.get("records")
    if not base or not isinstance(records, list):
        return data
    for record in records:
        if not isinstance(record, dict):
            continue
        url = record.get("url")
        if isinstance(url, str) and url.startswith("/"):
            record["url"] = f"{base}{url}"
    return data


def query_face_page(current: int, size: int, keyword: str | None = None) -> dict:
    """分页查询人脸照片库。

    Args:
        current: 页码（从 1 开始）。
        size: 每页条数。
        keyword: 描述信息 val 模糊匹配关键字，空则不筛选。

    Returns:
        外部接口 data 部分（PageBean：total/current/size/records），records 的 url 已补全为绝对地址。

    Raises:
        HTTPException: 服务未配置（500）、不可达（502）或业务码非成功（502）。
    """
    settings = get_settings()
    base_url = settings.face_photo_api_base_url
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
    if not isinstance(payload, dict) or not _is_success_code(payload.get("code")):
        message = payload.get("msg") if isinstance(payload, dict) else payload
        raise HTTPException(status_code=502, detail=f"Face photo API error: {message}")
    data = payload.get("data")
    if not isinstance(data, dict):
        return {}
    return _absolutize_record_urls(data, settings.face_photo_image_base_url)
