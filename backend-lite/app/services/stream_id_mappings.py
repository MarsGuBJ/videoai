"""MCP Server 流ID映射 HTTP 接口代理。"""

from typing import Any

import requests
from fastapi import HTTPException

from app.core.config import get_settings
from app.services.person_search import parse_person_api_response

MCP_TIMEOUT_SECONDS = 30
# 导入接口 MCP 侧要逐行校验 CVR 上的流ID（ISAPI 反查），给足超时
MCP_IMPORT_TIMEOUT_SECONDS = 120

# MCP error.type 中含这些关键词时视为参数类错误，透传为 400
_CLIENT_ERROR_KEYWORDS = ("invalid", "param", "argument", "value", "not_found", "notfound")


def _mcp_request(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    timeout: int = MCP_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """调用 MCP Server 的流ID映射 HTTP 接口并解析响应。

    Args:
        method: HTTP 方法（GET / POST）。
        path: 接口路径（如 /stream-id-mappings）。
        payload: JSON 请求体（仅 POST 使用）。
        timeout: 超时秒数。

    Returns:
        MCP 响应 JSON。

    Raises:
        HTTPException: 服务未配置（500）、不可达（502）、返回 error 负载
            （参数类错误 400，其余 502）或非 2xx。
    """
    base_url = get_settings().mcp_server_base_url
    if not base_url:
        raise HTTPException(status_code=500, detail="MCP_SERVER_BASE_URL is not configured")
    try:
        if method == "GET":
            response = requests.get(f"{base_url}{path}", timeout=timeout)
        else:
            response = requests.post(f"{base_url}{path}", json=payload, timeout=timeout)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"MCP server unavailable: {exc}") from exc
    result = parse_person_api_response(response)
    error = result.get("error")
    if isinstance(error, dict):
        message = error.get("message") or "unknown error"
        error_type = str(error.get("type") or "").lower()
        status_code = 400 if any(keyword in error_type for keyword in _CLIENT_ERROR_KEYWORDS) else 502
        raise HTTPException(status_code=status_code, detail=f"Stream ID mapping request failed: {message}")
    return result


def list_mappings() -> list[dict[str, Any]]:
    """调用 MCP GET /stream-id-mappings，返回流ID映射列表。

    Returns:
        MCP data 字段的映射列表（元素含 cameraHost/streamId/cvrHost/cvrPort/username）。
    """
    result = _mcp_request("GET", "/stream-id-mappings")
    data = result.get("data")
    if not isinstance(data, list):
        raise HTTPException(status_code=502, detail="Stream ID mapping list returned malformed data")
    return [item for item in data if isinstance(item, dict)]


def import_mappings(payload: dict[str, Any]) -> dict[str, Any]:
    """调用 MCP POST /stream-id-mappings/import，批量导入流ID映射。

    MCP 侧导入前会逐行校验 CVR 上是否查得到该流ID，查不到的跳过。

    Args:
        payload: 透传的导入请求体（{"rows": [...], "cvr": {...}}）。

    Returns:
        MCP data 字段（含 imported 数量与 skipped 跳过明细 [{row, reason}]）。
    """
    result = _mcp_request("POST", "/stream-id-mappings/import", payload, timeout=MCP_IMPORT_TIMEOUT_SECONDS)
    data = result.get("data")
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="Stream ID mapping import returned malformed data")
    return data
