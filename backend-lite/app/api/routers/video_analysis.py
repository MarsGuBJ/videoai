"""MinIO 视频智能分析代理路由。"""

from typing import Annotated, Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from app.schemas.video_analysis import RecordingFileRequest, VideoAnalysisRequest
from app.services import camera_cache
from app.services.person_search import required_text
from app.services.search_keywords import SEARCH_TYPE_TEXT_VIDEO, record_search_keyword
from app.services.video_analysis import extract_video_frame, mcp_recording_export, video_analysis_api_post
from app.services.video_storage import save_analysis_video

router = APIRouter()


@router.post("/api/video-analysis/analyze")
def video_analysis_analyze_proxy(request: VideoAnalysisRequest) -> dict[str, Any]:
    """代理：MinIO 视频智能分析（文搜视频）；记录关键词用于统计。"""
    prompt = required_text(request.prompt, "prompt")
    record_search_keyword(prompt, SEARCH_TYPE_TEXT_VIDEO)
    payload = {
        "video_url": required_text(request.videoUrl, "videoUrl"),
        "fps": max(1, int(request.fps)),
        "segment_seconds": max(1, int(request.segmentSeconds)),
        "max_segments": max(1, int(request.maxSegments)),
        "height": max(1, int(request.height)),
        "prompt": prompt,
    }
    return video_analysis_api_post("/analyze_minio_video", payload)


@router.post("/api/video-analysis/upload-video")
async def upload_analysis_video(file: UploadFile = File(...)) -> dict[str, Any]:  # noqa: B008  # FastAPI File 依赖注入惯例
    """上传本地视频到 MinIO，返回可供分析服务拉取的 videoUrl。"""
    return {"videoUrl": await save_analysis_video(file)}


@router.get("/api/video-analysis/frame")
def video_analysis_frame(video_url: Annotated[str, Query(alias="videoUrl")], seconds: float = 0) -> Response:
    """按时间点截取视频一帧 JPEG，供分析结果事件卡片直接作为 <img> 地址。"""
    frame = extract_video_frame(required_text(video_url, "videoUrl"), seconds)
    return Response(content=frame, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})


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
