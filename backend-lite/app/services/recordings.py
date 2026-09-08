"""MCP Server 录像检索 / 回放 / 下载 HTTP 接口代理。"""

from typing import Any

import requests
from fastapi import HTTPException

from app.core.config import get_settings
from app.services.person_search import parse_person_api_response

MCP_SEARCH_TIMEOUT_SECONDS = 30
MCP_STREAM_TIMEOUT_SECONDS = 60
# 下载耗时随时段增长（SDK 下载非实时），可能达数十秒~数分钟
MCP_DOWNLOAD_TIMEOUT_SECONDS = 1800

# MCP error.type 中含这些关键词时视为参数类错误，透传为 400
_CLIENT_ERROR_KEYWORDS = ("invalid", "param", "argument", "value", "not_found", "notfound")


def _mcp_recording_post(path: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    """POST 调用 MCP Server 的录像相关 HTTP 接口并解析响应。

    Args:
        path: 接口路径（如 /search_recordings-http）。
        payload: JSON 请求体。
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
        response = requests.post(f"{base_url}{path}", json=payload, timeout=timeout)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"MCP server unavailable: {exc}") from exc
    result = parse_person_api_response(response)
    error = result.get("error")
    if isinstance(error, dict):
        message = error.get("message") or "unknown error"
        error_type = str(error.get("type") or "").lower()
        status_code = 400 if any(keyword in error_type for keyword in _CLIENT_ERROR_KEYWORDS) else 502
        raise HTTPException(status_code=status_code, detail=f"Recording request failed: {message}")
    return result


def search_recordings(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """调用 MCP /search_recordings-http，返回录像段列表（时段无录像时为空列表）。

    Args:
        payload: 请求体（cameraId/startTime/endTime/autoProxy/streamFormat）。

    Returns:
        MCP data 字段的录像段列表。
    """
    result = _mcp_recording_post("/search_recordings-http", payload, MCP_SEARCH_TIMEOUT_SECONDS)
    data = result.get("data")
    if not isinstance(data, list):
        raise HTTPException(status_code=502, detail="Recording search returned malformed data")
    return [item for item in data if isinstance(item, dict)]


def get_recording_stream(payload: dict[str, Any]) -> dict[str, Any]:
    """调用 MCP /get_recording_stream-http，返回回放地址。

    Args:
        payload: 请求体（recordingId/format）。

    Returns:
        MCP 响应（含 url/format/expiresAt）。

    Raises:
        HTTPException: 响应缺 url 时 502。
    """
    result = _mcp_recording_post("/get_recording_stream-http", payload, MCP_STREAM_TIMEOUT_SECONDS)
    if not result.get("url"):
        raise HTTPException(status_code=502, detail="Recording stream returned no url")
    return result


def download_recording(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """调用 MCP /download_recording-http，返回下载结果列表（data[0].url 为 MP4 地址）。

    Args:
        payload: 请求体（cameraId/startTime/endTime）。

    Returns:
        MCP data 字段的结果列表。
    """
    result = _mcp_recording_post("/download_recording-http", payload, MCP_DOWNLOAD_TIMEOUT_SECONDS)
    data = result.get("data")
    if not isinstance(data, list):
        raise HTTPException(status_code=502, detail="Recording download returned malformed data")
    return [item for item in data if isinstance(item, dict)]
