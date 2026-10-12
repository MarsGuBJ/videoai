"""流ID映射代理路由。"""

from fastapi import APIRouter

from app.schemas.stream_id_mapping import (
    StreamIdImportRequest,
    StreamIdImportResponse,
    StreamIdMappingItem,
)
from app.services import stream_id_mappings

router = APIRouter(tags=["流ID映射"])


@router.get("/api/stream-id-mappings")
def list_stream_id_mappings() -> list[StreamIdMappingItem]:
    """返回全部流ID映射（摄像头流ID 与其所在 CVR 的关联）。"""
    data = stream_id_mappings.list_mappings()
    return [
        StreamIdMappingItem(
            cameraHost=str(item.get("cameraHost") or ""),
            streamId=str(item.get("streamId") or ""),
            cvrHost=str(item.get("cvrHost") or ""),
            cvrPort=int(item.get("cvrPort") or 0),
            username=str(item.get("username") or ""),
        )
        for item in data
    ]


@router.post("/api/stream-id-mappings/import")
def import_stream_id_mappings(request: StreamIdImportRequest) -> StreamIdImportResponse:
    """批量导入流ID映射（请求体透传给 MCP）。

    MCP 侧导入前逐行校验 CVR 上是否查得到该流ID，查不到的行
    不会导入，在 skipped 中返回原因。
    """
    data = stream_id_mappings.import_mappings(request.model_dump())
    skipped = data.get("skipped")
    return StreamIdImportResponse(
        imported=int(data.get("imported") or 0),
        skipped=[item for item in skipped if isinstance(item, dict)] if isinstance(skipped, list) else [],
    )
