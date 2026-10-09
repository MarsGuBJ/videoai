"""录像存储绑定代理路由。"""

from fastapi import APIRouter

from app.schemas.storage_binding import (
    ResolvedStorageBindingItem,
    StorageBindingItem,
    StorageBindRequest,
    StorageBindResponse,
    StorageBindSkippedItem,
    StorageUnbindRequest,
    StorageUnbindResponse,
)
from app.services import storage_bindings

router = APIRouter(tags=["录像存储绑定"])


@router.get("/api/storage-bindings")
def list_storage_bindings() -> list[StorageBindingItem]:
    """返回已绑定录像存储的摄像头列表（MCP 的 host 字段映射为 storageHost）。"""
    data = storage_bindings.list_bindings()
    return [
        StorageBindingItem(
            cameraId=str(item.get("cameraId") or ""),
            storageHost=str(item.get("host") or ""),
            username=str(item.get("username") or ""),
        )
        for item in data
    ]


@router.get("/api/storage-bindings/resolved")
def list_resolved_storage_bindings() -> list[ResolvedStorageBindingItem]:
    """返回各摄像头实际生效的录像存储设备（显式绑定 + 回放链路解析出的 NVR/CVR）。"""
    data = storage_bindings.list_resolved_bindings()
    return [
        ResolvedStorageBindingItem(
            cameraId=str(item.get("cameraId") or ""),
            storageHost=str(item.get("host") or ""),
            bound=bool(item.get("bound")),
        )
        for item in data
    ]


@router.post("/api/storage-bindings/bind")
def bind_storage(request: StorageBindRequest) -> StorageBindResponse:
    """把一批摄像头绑定到同一台录像存储主机。

    MCP 侧绑定前逐台校验存储设备上是否查得到该摄像头的录像，查不到的设备
    不会绑定，在 skipped 中返回原因。
    """
    data = storage_bindings.bind_bindings(
        request.cameraIds, request.storageHost, request.username, request.password
    )
    skipped = data.get("skipped")
    return StorageBindResponse(
        bound=int(data.get("bound") or 0),
        skipped=[
            StorageBindSkippedItem(cameraId=str(item.get("cameraId") or ""), reason=str(item.get("reason") or ""))
            for item in skipped
            if isinstance(item, dict)
        ]
        if isinstance(skipped, list)
        else [],
    )


@router.post("/api/storage-bindings/unbind")
def unbind_storage(request: StorageUnbindRequest) -> StorageUnbindResponse:
    """解绑一批摄像头的录像存储。"""
    data = storage_bindings.unbind_bindings(request.cameraIds)
    return StorageUnbindResponse(unbound=int(data.get("unbound") or 0))
