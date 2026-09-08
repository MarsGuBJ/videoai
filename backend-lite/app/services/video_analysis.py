"""MinIO 视频智能分析服务的外部 API 代理。"""

import subprocess
from typing import Any

import requests
from fastapi import HTTPException

from app.core.config import get_settings
from app.services.person_search import parse_person_api_response

VIDEO_ANALYSIS_API_TIMEOUT_SECONDS = 600
# 录像导出墙钟时间 ≈ 录像时长（约 1x 抓流），上限 1200s，留足余量
MCP_EXPORT_TIMEOUT_SECONDS = 1980
# 单帧截图：含远程视频寻址，给足网络与解码余量
VIDEO_FRAME_TIMEOUT_SECONDS = 60


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


def mcp_recording_export(payload: dict[str, Any]) -> dict[str, Any]:
    """POST 调用 MCP Server 的录像导出 HTTP 接口（/export_recording-http）。

    Args:
        payload: JSON 请求体（trackId/startTime/endTime）。

    Returns:
        MCP 响应中的 data 字典（含 videoUrl）。

    Raises:
        HTTPException: 服务未配置（500）、不可达（502）、返回 error 负载（502）或非 2xx。
    """
    base_url = get_settings().mcp_server_base_url
    if not base_url:
        raise HTTPException(status_code=500, detail="MCP_SERVER_BASE_URL is not configured")
    try:
        response = requests.post(f"{base_url}/export_recording-http", json=payload, timeout=MCP_EXPORT_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"MCP server unavailable: {exc}") from exc
    result = parse_person_api_response(response)
    error = result.get("error")
    if isinstance(error, dict):
        raise HTTPException(status_code=502, detail=f"Recording export failed: {error.get('message')}")
    data = result.get("data")
    if not isinstance(data, dict) or not data.get("videoUrl"):
        raise HTTPException(status_code=502, detail="Recording export returned no videoUrl")
    return data


def extract_video_frame(video_url: str, seconds: float) -> bytes:
    """用 ffmpeg 从视频文件的指定时间点截取一帧 JPEG。

    Args:
        video_url: 视频文件 URL（MinIO 等 HTTP 地址）。
        seconds: 截图时间点（秒，从 0 开始）。

    Returns:
        JPEG 字节。

    Raises:
        HTTPException: 地址不合法（400）或截图失败（502）。
    """
    url = video_url.strip()
    if not url.lower().startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="videoUrl 必须是 http(s) 视频文件地址")
    offset = max(0.0, float(seconds))
    try:
        process = subprocess.run(  # noqa: S603  # 参数列表固定，地址来自已确认的分析视频源
            [
                get_settings().ffmpeg_bin,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                f"{offset:.3f}",
                "-i",
                url,
                "-frames:v",
                "1",
                "-q:v",
                "3",
                "-f",
                "image2pipe",
                "-vcodec",
                "mjpeg",
                "pipe:1",
            ],
            capture_output=True,
            timeout=VIDEO_FRAME_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(status_code=502, detail=f"Frame extraction failed: {exc}") from exc
    if process.returncode != 0 or not process.stdout:
        raise HTTPException(status_code=502, detail="Frame extraction returned no image")
    return process.stdout
