"""MinIO 媒体文件同源代理路由（搜索结果图片/短视频经 5173 nginx 反代拉取）。"""

from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from app.services.minio_files import open_minio_object_stream
from app.services.person_search import required_text

router = APIRouter(tags=["MinIO 文件代理"])

OBJECT_STREAM_PASSTHROUGH_HEADERS = (
    "content-length",
    "content-range",
    "accept-ranges",
    "content-type",
    "etag",
    "last-modified",
)


@router.get("/api/minio/files")
def minio_file_proxy(request: Request, url: Annotated[str, Query(alias="url")]) -> StreamingResponse:
    """代理 MinIO 对象（人员图片/事件短视频）：同源反代，Range 透传支持视频 seek。

    只接受当前部署 MinIO 的地址（见 services.minio_files.is_minio_url），
    避免被当作开放代理滥用。
    """
    upstream = open_minio_object_stream(required_text(url, "url"), request.headers.get("range"))
    headers = {
        key: value for key, value in upstream.headers.items() if key.lower() in OBJECT_STREAM_PASSTHROUGH_HEADERS
    }
    headers["X-Accel-Buffering"] = "no"

    def body() -> Iterator[bytes]:
        try:
            yield from upstream.iter_content(chunk_size=256 * 1024)
        finally:
            upstream.close()

    return StreamingResponse(body(), status_code=upstream.status_code, headers=headers)
