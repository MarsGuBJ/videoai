"""MCP Server 录像存储绑定 HTTP 接口代理。"""

from typing import Any

import requests
from fastapi import HTTPException

from app.core.config import get_settings
from app.services.person_search import parse_person_api_response

MCP_TIMEOUT_SECONDS = 30
# 绑定接口 MCP 侧要逐台校验存储设备录像（ISAPI 反查 + 检索），给足超时
MCP_BIND_TIMEOUT_SECONDS = 120

# MCP error.type 中含这些关键词时视为参数类错误，透传为 400
_CLIENT_ERROR_KEYWORDS = ("invalid", "param", "argument", "value", "not_found", "notfound")


def _mcp_request(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    timeout: int = MCP_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """调用 MCP Server 的存储绑定 HTTP 接口并解析响应。

    Args:
        method: HTTP 方法（GET / POST）。
        path: 接口路径（如 /storage-bindings）。
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
        raise HTTPException(status_code=status_code, detail=f"Storage binding request failed: {message}")
    return result


def list_bindings() -> list[dict[str, Any]]:
    """调用 MCP GET /storage-bindings，返回绑定关系列表。

    Returns:
        MCP data 字段的绑定列表（元素含 cameraId/host/username）。
    """
    result = _mcp_request("GET", "/storage-bindings")
    data = result.get("data")
    if not isinstance(data, list):
        raise HTTPException(status_code=502, detail="Storage binding list returned malformed data")
    return [item for item in data if isinstance(item, dict)]


def list_resolved_bindings() -> list[dict[str, Any]]:
    """调用 MCP GET /storage-bindings/resolved，返回各摄像头实际生效的存储设备。

    Returns:
        MCP data 字段的列表（元素含 cameraId/host/bound）。
    """
    result = _mcp_request("GET", "/storage-bindings/resolved")
    data = result.get("data")
    if not isinstance(data, list):
        raise HTTPException(status_code=502, detail="Resolved storage binding list returned malformed data")
    return [item for item in data if isinstance(item, dict)]


def bind_bindings(camera_ids: list[str], host: str, username: str, password: str) -> dict[str, Any]:
    """调用 MCP POST /storage-bindings/bind，把一批摄像头绑定到同一存储主机。

    MCP 侧绑定前会逐台校验存储设备上是否查得到该摄像头的录像，查不到的跳过。

    Args:
        camera_ids: 摄像头 ID 列表。
        host: 存储主机地址。
        username: 存储主机账号。
        password: 存储主机密码（仅随请求转发，不记日志）。

    Returns:
        MCP data 字段（含 bound 数量与 skipped 跳过明细 [{cameraId, reason}]）。
    """
    payload = {
        "items": [
            {"cameraId": camera_id, "host": host, "username": username, "password": password}
            for camera_id in camera_ids
        ]
    }
    result = _mcp_request("POST", "/storage-bindings/bind", payload, timeout=MCP_BIND_TIMEOUT_SECONDS)
    data = result.get("data")
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="Storage bind returned malformed data")
    return data


def unbind_bindings(camera_ids: list[str]) -> dict[str, Any]:
    """调用 MCP POST /storage-bindings/unbind，解绑一批摄像头。

    Returns:
        MCP data 字段（含 unbound 数量）。
    """
    result = _mcp_request("POST", "/storage-bindings/unbind", {"cameraIds": list(camera_ids)})
    data = result.get("data")
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="Storage unbind returned malformed data")
    return data
