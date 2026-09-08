"""Worker 节点资源监控路由：心跳上报（内网）与节点列表查询（前端）。"""

from fastapi import APIRouter

from app import state
from app.schemas.worker_node import WorkerHeartbeatIn, WorkerNodeOut
from app.services.worker_nodes import record_worker_heartbeat, worker_node_out

router = APIRouter()


@router.post("/api/internal/workers/heartbeat", response_model=WorkerNodeOut)
def worker_heartbeat(request: WorkerHeartbeatIn) -> WorkerNodeOut:
    """接收 worker 心跳：upsert 节点注册表并返回当前节点视图。"""
    record = record_worker_heartbeat(request)
    return worker_node_out(record)


@router.get("/api/worker-nodes", response_model=list[WorkerNodeOut])
def list_worker_nodes() -> list[WorkerNodeOut]:
    """按 hostname 排序返回全部 worker 节点。"""
    records = sorted(state.worker_nodes_store.values(), key=lambda item: str(item["hostname"]))
    return [worker_node_out(record) for record in records]
