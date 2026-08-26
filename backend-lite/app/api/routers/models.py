"""模型管理（Triton）路由。"""

from datetime import datetime, timezone
from urllib.parse import quote
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app import state
from app.schemas.model import ModelGpuResponse, ModelGpuUpdateRequest, ModelRegisterRequest, ModelResponse
from app.services.triton import (
    model_config_path,
    normalize_gpu_ids,
    parse_model_gpu_ids,
    refresh_model_states,
    reload_triton_model,
    require_model,
    triton_request,
    update_model_gpu_pbtxt,
    update_model_state,
)

router = APIRouter()


@router.get("/api/models")
def models() -> list[ModelResponse]:
    """刷新状态后按创建时间倒序返回全部注册模型。"""
    refresh_model_states()
    return sorted(state.model_registry.values(), key=lambda item: item.createdAt, reverse=True)


@router.post("/api/models/register", response_model=ModelResponse)
def register_model(request: ModelRegisterRequest) -> ModelResponse:
    """注册（或更新）一个模型条目。"""
    if not request.name.strip():
        raise HTTPException(status_code=400, detail="Model name is required")
    if not request.displayName.strip():
        raise HTTPException(status_code=400, detail="Display name is required")
    now = datetime.now(timezone.utc)
    current = state.model_registry.get(request.name)
    model = ModelResponse(
        id=current.id if current else uuid4(),
        name=request.name,
        displayName=request.displayName,
        repositoryPath=request.repositoryPath or f"/models/{request.name}",
        modelType=request.modelType,
        description=request.description or None,
        state=current.state if current else "UNKNOWN",
        createdAt=current.createdAt if current else now,
        updatedAt=now,
    )
    state.model_registry[request.name] = model
    refresh_model_states()
    return state.model_registry[request.name]


@router.post("/api/models/{model_name}/load", response_model=ModelResponse)
def load_model(model_name: str) -> ModelResponse:
    """请求 Triton 加载模型。"""
    require_model(model_name)
    triton_request(f"/v2/repository/models/{quote(model_name, safe='')}/load", method="POST", payload={})
    update_model_state(model_name, "LOADING")
    refresh_model_states()
    return state.model_registry[model_name]


@router.post("/api/models/{model_name}/unload", response_model=ModelResponse)
def unload_model(model_name: str) -> ModelResponse:
    """请求 Triton 卸载模型。"""
    require_model(model_name)
    triton_request(f"/v2/repository/models/{quote(model_name, safe='')}/unload", method="POST", payload={})
    update_model_state(model_name, "UNLOADING")
    refresh_model_states()
    return state.model_registry[model_name]


@router.get("/api/models/{model_name}/config")
def model_config(model_name: str) -> dict:
    """返回模型的 Triton 配置。"""
    require_model(model_name)
    config = triton_request(f"/v2/models/{quote(model_name, safe='')}/config", method="GET")
    return {"name": model_name, "config": config}


@router.get("/api/models/{model_name}/gpu", response_model=ModelGpuResponse)
def model_gpu_config(model_name: str) -> ModelGpuResponse:
    """读取模型 config.pbtxt 中的 GPU 分配。"""
    require_model(model_name)
    config_path = model_config_path(model_name)
    return ModelGpuResponse(
        modelName=model_name,
        gpuIds=parse_model_gpu_ids(config_path.read_text(encoding="utf-8")),
        configPath=str(config_path),
    )


@router.patch("/api/models/{model_name}/gpu", response_model=ModelGpuResponse)
def update_model_gpu_config(model_name: str, request: ModelGpuUpdateRequest) -> ModelGpuResponse:
    """重写模型 GPU 分配并重载模型。"""
    require_model(model_name)
    gpu_ids = normalize_gpu_ids(request.gpuIds)
    config_path = model_config_path(model_name)
    current = config_path.read_text(encoding="utf-8")
    config_path.write_text(update_model_gpu_pbtxt(current, gpu_ids), encoding="utf-8")
    reload_triton_model(model_name)
    return ModelGpuResponse(modelName=model_name, gpuIds=gpu_ids, configPath=str(config_path))
