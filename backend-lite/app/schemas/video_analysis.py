"""MinIO 视频智能分析 DTO。"""

from pydantic import BaseModel


class VideoAnalysisRequest(BaseModel):
    videoUrl: str
    prompt: str
    fps: int = 1
    segmentSeconds: int = 60
    maxSegments: int = 1
    height: int = 480
