"""MinIO 视频智能分析代理路由。"""

from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response, StreamingResponse

from app.schemas.video_analysis import RecordingFileRequest, VideoAnalysisRequest
from app.services import camera_cache
from app.services.person_search import required_text
from app.services.search_keywords import SEARCH_TYPE_TEXT_VIDEO, record_search_keyword
from app.services.video_analysis import extract_video_frame, mcp_recording_export, open_video_stream, video_analysis_api_post
from app.services.video_storage import save_analysis_video

router = APIRouter()

# 代理播放时透传给客户端的上游响应头
VIDEO_STREAM_PASSTHROUGH_HEADERS = ("content-length", "content-range", "accept-ranges", "content-type", "etag", "last-modified")


@router.post("/api/video-analysis/analyze")
def video_analysis_analyze_proxy(request: VideoAnalysisRequest) -> dict[str, Any]:
    """代理：视频理解结构化接口（文搜视频，见《视频理解接口0910》）；记录关键词用于统计。"""
    prompt = required_text(request.prompt, "prompt")
    record_search_keyword(prompt, SEARCH_TYPE_TEXT_VIDEO)
    payload = {
        "video_url": required_text(request.videoUrl, "videoUrl"),
        # 未单独传 question 时以 prompt 作为用户问题
        "question": (request.question or "").strip() or prompt,
        "fps": max(1, int(request.fps)),
        "segment_seconds": max(1, int(request.segmentSeconds)),
        "max_segments": max(1, int(request.maxSegments)),
        "height": max(1, int(request.height)),
        "prompt": prompt,
    }
    return video_analysis_api_post("/api/v1/video-understanding/structure", payload)


@router.post("/api/video-analysis/upload-video")
async def upload_analysis_video(file: UploadFile = File(...)) -> dict[str, Any]:  # noqa: B008  # FastAPI File 依赖注入惯例
    """上传本地视频到 MinIO，返回可供分析服务拉取的 videoUrl。"""
    return {"videoUrl": await save_analysis_video(file)}


@router.get("/api/video-analysis/frame")
def video_analysis_frame(
    video_url: Annotated[str, Query(alias="videoUrl")],
    seconds: float = 0,
    width: int | None = None,
) -> Response:
    """按时间点截取视频一帧 JPEG，供分析结果事件卡片直接作为 <img> 地址。

    width 可选：缩略图场景按宽度缩放（保持宽高比）减小传输体积，缺省返回原尺寸。
    """
    frame = extract_video_frame(required_text(video_url, "videoUrl"), seconds, width)
    return Response(content=frame, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})


@router.get("/api/video-analysis/video")
def video_analysis_video_proxy(request: Request, video_url: Annotated[str, Query(alias="videoUrl")]) -> StreamingResponse:
    """代理播放分析视频文件：Range 透传支持 seek；同源反代避免浏览器直连 MinIO 被现场链路限速。"""
    upstream = open_video_stream(required_text(video_url, "videoUrl"), request.headers.get("range"))
    headers = {key: value for key, value in upstream.headers.items() if key.lower() in VIDEO_STREAM_PASSTHROUGH_HEADERS}
    headers["X-Accel-Buffering"] = "no"

    def body() -> Iterator[bytes]:
        try:
            yield from upstream.iter_content(chunk_size=256 * 1024)
        finally:
            upstream.close()

    return StreamingResponse(body(), status_code=upstream.status_code, headers=headers)


@router.post("/api/video-analysis/recording-file")
def recording_file_proxy(request: RecordingFileRequest) -> dict[str, Any]:
    """按摄像头与时间段导出 NVR 录像为 MP4，返回可分析的文件 URL。

    直连 IPC 的摄像头由 MCP 端反查其所属 NVR 通道，无需平台侧 nvrTrackId。
    """
    camera_id = required_text(request.cameraId, "cameraId")
    start_time = required_text(request.startTime, "startTime")
    end_time = required_text(request.endTime, "endTime")
    camera = camera_cache.get(camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    track_id = (camera.nvrTrackId or "").strip()
    return mcp_recording_export(
        {"cameraId": camera_id, "trackId": track_id, "startTime": start_time, "endTime": end_time}
    )
