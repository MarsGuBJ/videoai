"""MinIO 视频智能分析代理路由。"""

from typing import Any

from fastapi import APIRouter

from app.schemas.video_analysis import VideoAnalysisRequest
from app.services.person_search import required_text
from app.services.video_analysis import video_analysis_api_post

router = APIRouter()


@router.post("/api/video-analysis/analyze")
def video_analysis_analyze_proxy(request: VideoAnalysisRequest) -> dict[str, Any]:
    """代理：MinIO 视频智能分析（文搜视频）。"""
    payload = {
        "video_url": required_text(request.videoUrl, "videoUrl"),
        "fps": max(1, int(request.fps)),
        "segment_seconds": max(1, int(request.segmentSeconds)),
        "max_segments": max(1, int(request.maxSegments)),
        "height": max(1, int(request.height)),
        "prompt": required_text(request.prompt, "prompt"),
    }
    return video_analysis_api_post("/analyze_minio_video", payload)
