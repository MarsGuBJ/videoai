"""NVR 录像检索 / 回放 / 下载代理路由。"""

from fastapi import APIRouter, HTTPException

from app.schemas.camera import CameraResponse
from app.schemas.recordings import (
    RecordingDownloadResponse,
    RecordingSearchRequest,
    RecordingSearchResponse,
    RecordingSegment,
    RecordingStreamResponse,
)
from app.services import camera_cache
from app.services.person_search import required_text
from app.services.recordings import download_recording, search_recordings

router = APIRouter()

STREAM_FORMAT = "flv"
# 与 MCP PLAYBACK_SPEEDS 一致：现场海康 NVR（10.10.7.252/253）RTSP 回放 Scale 实测支持档位
PLAYBACK_SPEEDS = (0.25, 0.5, 1, 2, 4, 8, 16, 32)


def _resolve_camera(request: RecordingSearchRequest) -> tuple[CameraResponse, str, str, str]:
    """校验请求字段、摄像头存在。

    不再在此拦截"未绑定 NVR"：直连 IPC 的摄像头由 MCP 端反查其所属 NVR 通道；
    反查未命中且未绑定时由 MCP 返回参数错误（透传为 400）。

    Returns:
        (camera, cameraId, startTime, endTime)。

    Raises:
        HTTPException: 字段空白（400）、摄像头不存在（404）。
    """
    camera_id = required_text(request.cameraId, "cameraId")
    start_time = required_text(request.startTime, "startTime")
    end_time = required_text(request.endTime, "endTime")
    camera = camera_cache.get(camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera, camera_id, start_time, end_time


@router.post("/api/recordings/search")
def recordings_search(request: RecordingSearchRequest) -> RecordingSearchResponse:
    """检索摄像头在指定时段的 NVR 录像段列表。"""
    _camera, camera_id, start_time, end_time = _resolve_camera(request)
    data = search_recordings(
        {
            "cameraId": camera_id,
            "startTime": start_time,
            "endTime": end_time,
            "autoProxy": False,
            "streamFormat": STREAM_FORMAT,
        }
    )
    return RecordingSearchResponse(data=[RecordingSegment(**item) for item in data])


@router.post("/api/recordings/stream")
def recordings_stream(request: RecordingSearchRequest) -> RecordingStreamResponse:
    """检索录像并返回第一段录像的按需回放链接（/recording-live 动态链接，speed 指定回放倍速）。

    链接在首次请求时才建立 SDK 回放流，因此这里直接返回链接而不预建流。
    MCP 侧的 get_recording_stream 仍保留为 HTTP 兼容接口（返回 H.265 直通流），
    但不是 MCP tool，且只支持等速，本接口的倍速回放继续走 /recording-live。
    """
    _camera, camera_id, start_time, end_time = _resolve_camera(request)
    speed = request.speed if request.speed is not None else 1.0
    if speed not in PLAYBACK_SPEEDS:
        raise HTTPException(status_code=400, detail=f"不支持的回放倍速: {speed}")
    data = search_recordings(
        {
            "cameraId": camera_id,
            "startTime": start_time,
            "endTime": end_time,
            "autoProxy": True,
            "streamFormat": STREAM_FORMAT,
        }
    )
    if not data:
        raise HTTPException(status_code=404, detail="该时段无录像")
    url = required_text(str(data[0].get("url") or ""), "url")
    return RecordingStreamResponse(url=f"{url}&speed={speed}", format=STREAM_FORMAT, expiresAt=None)


@router.post("/api/recordings/download")
def recordings_download(request: RecordingSearchRequest) -> RecordingDownloadResponse:
    """导出摄像头指定时段录像为 MP4，返回可下载的 MinIO 地址。"""
    _camera, camera_id, start_time, end_time = _resolve_camera(request)
    data = download_recording({"cameraId": camera_id, "startTime": start_time, "endTime": end_time})
    if not data or not data[0].get("url"):
        raise HTTPException(status_code=502, detail="Recording download returned no url")
    return RecordingDownloadResponse(url=data[0]["url"], format=data[0].get("format") or "mp4")
