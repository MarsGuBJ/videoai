"""视频理解结果结构化展示服务（/api/v1/video-understanding/structure）的异步客户端。"""

from typing import Any

import httpx

from .person_api_client import parse_response, required

# 上游接口的默认分析提示词（见《视频理解接口0910》文档）
DEFAULT_PROMPT = "请分析视频中的主要人员、物体、行为及异常事件"


class VideoUnderstandingClient:
    def __init__(self, base_url: str, timeout: float = 600, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.transport = transport

    async def structure(
        self,
        video_url: str,
        question: str,
        fps: int = 1,
        segment_seconds: int = 60,
        max_segments: int = 0,
        height: int = 480,
        prompt: str = DEFAULT_PROMPT,
    ) -> dict[str, Any]:
        """调用视频理解结构化接口：上游先做视频理解，再用 DeepSeek 整理为结构化事件并截取关键帧。

        响应原样透传（code/message/data，data 含 summary/answer_status/focus_event/events 等）。
        """
        payload: dict[str, Any] = {
            "video_url": required(video_url, "videoUrl"),
            "question": required(question, "question"),
            "fps": max(1, int(fps)),
            "segment_seconds": max(1, int(segment_seconds)),
            # max_segments 为 0 表示全部分析，不接受负数
            "max_segments": max(0, int(max_segments)),
            "height": max(1, int(height)),
            "prompt": str(prompt or "").strip() or DEFAULT_PROMPT,
        }
        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            response = await client.post(f"{self.base_url}/api/v1/video-understanding/structure", json=payload)
        return parse_response(response)
