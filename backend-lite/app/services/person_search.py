"""以图搜人 / 文本检索的外部 API 代理。"""

import requests
from fastapi import HTTPException

from app.core.config import get_settings

PERSON_API_TIMEOUT_SECONDS = 60
RETRIEVE_API_TIMEOUT_SECONDS = 120
ES_DOCUMENT_API_TIMEOUT_SECONDS = 60


def required_text(value: str, name: str) -> str:
    """校验字符串非空（strip 后），为空则 400。

    Args:
        value: 原始值。
        name: 字段名（用于错误信息）。

    Returns:
        strip 后的非空字符串。

    Raises:
        HTTPException: 空白字符串时 400。
    """
    normalized = str(value or "").strip()
    if not normalized:
        raise HTTPException(status_code=400, detail=f"{name} is required")
    return normalized


def absolutize_image_url(value: str) -> str:
    """把后端自身的相对资源路径补全为公网绝对地址。

    外部以图搜人服务只接受 http(s) 地址或 base64：前端传 ``/api/assets/...`` 这类
    相对路径时会被当成 base64 解析并报 "Incorrect padding"，检索直接失败。
    这里按 BACKEND_PUBLIC_URL 补全；已是绝对地址或 data:/blob: 的原样返回。

    Args:
        value: 图片地址（调用方已用 required_text 校验非空）。

    Returns:
        外部服务可拉取的绝对地址；未配置公网地址且入参为相对路径时原样返回。
    """
    text = str(value or "").strip()
    if not text or text.lower().startswith(("http://", "https://", "data:", "blob:", "//")):
        return text
    if not text.startswith("/"):
        return text
    public_base = (get_settings().backend_public_url or "").rstrip("/")
    return f"{public_base}{text}" if public_base else text


def person_api_post(path: str, payload: dict) -> dict:
    """POST 调用以图搜人服务。

    Args:
        path: API 路径。
        payload: JSON 请求体。

    Returns:
        解析后的响应 JSON。

    Raises:
        HTTPException: 服务未配置（500）、不可达（502）或返回非 2xx。
    """
    base_url = get_settings().person_api_base_url
    if not base_url:
        raise HTTPException(status_code=500, detail="PERSON_API_BASE_URL is not configured")
    try:
        response = requests.post(f"{base_url}{path}", json=payload, timeout=PERSON_API_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Person search API unavailable: {exc}") from exc
    return parse_person_api_response(response)


def person_api_get(path: str) -> dict:
    """GET 调用以图搜人服务。

    Args:
        path: API 路径。

    Returns:
        解析后的响应 JSON。

    Raises:
        HTTPException: 服务未配置（500）、不可达（502）或返回非 2xx。
    """
    base_url = get_settings().person_api_base_url
    if not base_url:
        raise HTTPException(status_code=500, detail="PERSON_API_BASE_URL is not configured")
    try:
        response = requests.get(f"{base_url}{path}", timeout=PERSON_API_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Person search API unavailable: {exc}") from exc
    return parse_person_api_response(response)


def parse_person_api_response(response: requests.Response) -> dict:
    """解析外部检索服务响应：2xx 返回 JSON，否则按原状态码透传。

    Args:
        response: requests 响应对象。

    Returns:
        响应 JSON（非 dict 时包装为 {"data": ...}）。

    Raises:
        HTTPException: 非 2xx 时按原状态码与响应体抛出。
    """
    try:
        payload = response.json()
    except ValueError:
        payload = {"message": response.text}
    if 200 <= response.status_code < 300:
        return payload if isinstance(payload, dict) else {"data": payload}
    raise HTTPException(status_code=response.status_code, detail=payload)


def retrieve_api_post(path: str, payload: dict) -> dict:
    """POST 调用文本检索服务。

    Args:
        path: API 路径。
        payload: JSON 请求体。

    Returns:
        解析后的响应 JSON。

    Raises:
        HTTPException: 服务未配置（500）、不可达（502）或返回非 2xx。
    """
    base_url = get_settings().retrieve_api_base_url
    if not base_url:
        raise HTTPException(status_code=500, detail="RETRIEVE_API_BASE_URL is not configured")
    try:
        response = requests.post(f"{base_url}{path}", json=payload, timeout=RETRIEVE_API_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Text search API unavailable: {exc}") from exc
    return parse_person_api_response(response)


def es_document_api_post(path: str, payload: dict) -> dict:
    """POST 调用 ES 文档查询接口（按 es_id 批量取人员图片文档）。

    Args:
        path: API 路径。
        payload: JSON 请求体。

    Returns:
        解析后的响应 JSON。

    Raises:
        HTTPException: 服务未配置（500）、不可达（502）或返回非 2xx。
    """
    base_url = get_settings().es_document_api_base_url
    if not base_url:
        raise HTTPException(status_code=500, detail="ES_DOCUMENT_API_BASE_URL is not configured")
    try:
        response = requests.post(f"{base_url}{path}", json=payload, timeout=ES_DOCUMENT_API_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"ES document API unavailable: {exc}") from exc
    return parse_person_api_response(response)
