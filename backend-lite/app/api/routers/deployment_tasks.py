"""布控任务 CRUD 路由。"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException

from app import state
from app.schemas.deployment_task import (
    DEFAULT_RECOGNITION_PER_MINUTE,
    DeploymentTaskCreateRequest,
    DeploymentTaskResponse,
    DeploymentTaskUpdateRequest,
)
from app.services.deployment_tasks import (
    clean_optional,
    delete_deployment_task_from_db,
    persist_deployment_task,
    require_deployment_task,
)
from app.services.worker_streams import sync_worker_streams_for_task

router = APIRouter()


@router.get("/api/deployment-tasks", response_model=list[DeploymentTaskResponse])
def list_deployment_tasks() -> list[DeploymentTaskResponse]:
    """按创建时间倒序返回全部布控任务。"""
    return sorted(state.deployment_tasks_store.values(), key=lambda item: item.createdAt, reverse=True)


@router.post("/api/deployment-tasks", response_model=DeploymentTaskResponse)
def create_deployment_task(request: DeploymentTaskCreateRequest) -> DeploymentTaskResponse:
    """创建布控任务：入内存、落库并同步 worker 流。"""
    task_id = uuid4()
    now = datetime.now(timezone.utc)
    task = DeploymentTaskResponse(
        id=task_id,
        name=request.name,
        pipeline=request.pipeline,
        area=clean_optional(request.area) or "默认区域",
        areaCount=max(0, int(request.areaCount or 0)),
        enabled=bool(request.enabled),
        taskStatus="stopped" if not request.enabled else "running",
        desc=request.desc or "",
        faceProfileId=request.faceProfileId,
        faceProfileName=clean_optional(request.faceProfileName),
        faceProfilePhotoUrl=clean_optional(request.faceProfilePhotoUrl),
        cameraIds=list(request.cameraIds or []),
        recognitionPerMinute=max(1, int(request.recognitionPerMinute or DEFAULT_RECOGNITION_PER_MINUTE)),
        createdAt=now,
        updatedAt=now,
    )
    state.deployment_tasks_store[task_id] = task
    persist_deployment_task(task)
    sync_worker_streams_for_task(task)
    return task


@router.get("/api/deployment-tasks/{task_id}", response_model=DeploymentTaskResponse)
def get_deployment_task(task_id: UUID) -> DeploymentTaskResponse:
    """按 ID 返回单个布控任务。"""
    return require_deployment_task(task_id)


@router.patch("/api/deployment-tasks/{task_id}", response_model=DeploymentTaskResponse)
def update_deployment_task(task_id: UUID, request: DeploymentTaskUpdateRequest) -> DeploymentTaskResponse:
    """部分更新布控任务；仅更新请求中显式出现的字段。"""
    old = require_deployment_task(task_id)
    update_payload: dict = {"updatedAt": datetime.now(timezone.utc)}
    if request.name is not None:
        update_payload["name"] = request.name
    if request.pipeline is not None:
        update_payload["pipeline"] = request.pipeline
    if request.area is not None:
        update_payload["area"] = request.area
    elif "area" in request.model_fields_set and request.area is None:
        update_payload["area"] = ""
    if request.areaCount is not None:
        update_payload["areaCount"] = max(0, int(request.areaCount))
    if request.enabled is not None:
        update_payload["enabled"] = bool(request.enabled)
        if "taskStatus" not in request.model_fields_set:
            update_payload["taskStatus"] = "running" if request.enabled else "stopped"
    if request.taskStatus is not None:
        update_payload["taskStatus"] = request.taskStatus
    if request.desc is not None:
        update_payload["desc"] = request.desc
    if request.faceProfileId is not None or "faceProfileId" in request.model_fields_set:
        update_payload["faceProfileId"] = request.faceProfileId
    if request.faceProfileName is not None or "faceProfileName" in request.model_fields_set:
        update_payload["faceProfileName"] = clean_optional(request.faceProfileName)
    if request.faceProfilePhotoUrl is not None or "faceProfilePhotoUrl" in request.model_fields_set:
        update_payload["faceProfilePhotoUrl"] = clean_optional(request.faceProfilePhotoUrl)
    if request.cameraIds is not None:
        update_payload["cameraIds"] = list(request.cameraIds)
    if request.recognitionPerMinute is not None:
        update_payload["recognitionPerMinute"] = max(1, int(request.recognitionPerMinute))
    updated = old.model_copy(update=update_payload)
    state.deployment_tasks_store[task_id] = updated
    persist_deployment_task(updated)
    sync_worker_streams_for_task(old)
    sync_worker_streams_for_task(updated)
    return updated


@router.delete("/api/deployment-tasks/{task_id}")
def delete_deployment_task(task_id: UUID) -> dict:
    """删除布控任务：移出内存、删库并同步 worker 流。"""
    task = state.deployment_tasks_store.pop(task_id, None)
    if not task:
        raise HTTPException(status_code=404, detail="Deployment task not found")
    delete_deployment_task_from_db(task_id)
    sync_worker_streams_for_task(task)
    return {"deleted": str(task_id)}
