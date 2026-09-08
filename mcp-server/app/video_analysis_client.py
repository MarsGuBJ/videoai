"""MinIO 视频智能分析服务（/analyze_minio_video）的异步客户端。"""

from typing import Any

import httpx

from .person_api_client import parse_response, required


class VideoAnalysisClient:
    def __init__(self, base_url: str, timeout: float = 600, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.transport = transport

    async def analyze_minio_video(
        self,
        video_url: str,
        prompt: str,
        fps: int = 1,
        segment_seconds: int = 60,
        max_segments: int = 1,
        height: int = 480,
    ) -> dict[str, Any]:
        """按抽帧/分段规则对视频文件做 AI 分析，透传分析服务响应。"""
        payload: dict[str, Any] = {
            "video_url": required(video_url, "videoUrl"),
            "fps": max(1, int(fps)),
            "segment_seconds": max(1, int(segment_seconds)),
            "max_segments": max(1, int(max_segments)),
            "height": max(1, int(height)),
            "prompt": required(prompt, "prompt"),
        }
        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            response = await client.post(f"{self.base_url}/analyze_minio_video", json=payload)
        return parse_response(response)
