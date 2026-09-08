"""文本检索服务（文搜图，/v1/retrieve/query）的异步客户端。"""

from typing import Any

import httpx

from .person_api_client import parse_response, required

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100


class RetrieveApiClient:
    def __init__(self, base_url: str, timeout: float = 120, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.transport = transport

    async def text_search(
        self,
        message: str,
        start_time: str = "",
        end_time: str = "",
        location: str = "",
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> dict[str, Any]:
        """自然语言检索人员/车辆图片，透传检索服务响应（session_id/items 等）。"""
        payload: dict[str, Any] = {
            "message": required(message, "message"),
            "start_time": start_time or None,
            "end_time": end_time or None,
            "location": location or None,
            "page": max(1, int(page)),
            "page_size": max(1, min(int(page_size), MAX_PAGE_SIZE)),
        }
        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            response = await client.post(f"{self.base_url}/v1/retrieve/query", json=payload)
        return parse_response(response)
