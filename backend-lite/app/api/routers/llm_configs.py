"""大模型配置 CRUD 与连接检测路由。"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app import state
from app.schemas.llm_config import LlmConfigCreate, LlmConfigOut, LlmConfigUpdate, LlmTestResult
from app.services.llm_configs import (
    delete_llm_config_from_db,
    llm_config_out,
    persist_llm_config,
    require_llm_config,
    test_llm_connection,
)

router = APIRouter()


@router.get("/api/llm-configs", response_model=list[LlmConfigOut])
def list_llm_configs() -> list[LlmConfigOut]:
    """按创建时间倒序返回全部大模型配置（apiKey 掩码）。"""
    records = sorted(state.llm_configs_store.values(), key=lambda item: item["created_at"], reverse=True)
    return [llm_config_out(record) for record in records]


@router.post("/api/llm-configs", response_model=LlmConfigOut)
def create_llm_config(request: LlmConfigCreate) -> LlmConfigOut:
    """创建大模型配置：生成 uuid，入内存并落库。"""
    config_id = str(uuid4())
    now = datetime.now(timezone.utc)
    record = {
        "id": config_id,
        "name": request.name,
        "base_url": request.baseUrl,
        "api_key": request.apiKey or "",
        "deploy_type": request.deployType,
        "timeout": request.timeout,
        "temperature": request.temperature,
        "max_tokens": request.maxTokens,
        "fps": request.fps,
        "created_at": now,
        "updated_at": now,
    }
    state.llm_configs_store[config_id] = record
    persist_llm_config(record)
    return llm_config_out(record)


@router.put("/api/llm-configs/{config_id}", response_model=LlmConfigOut)
def update_llm_config(config_id: str, request: LlmConfigUpdate) -> LlmConfigOut:
    """更新大模型配置；apiKey 传空字符串/None 时保留原值。"""
    record = require_llm_config(config_id)
    if request.name is not None:
        record["name"] = request.name
    if request.baseUrl is not None:
        record["base_url"] = request.baseUrl
    if request.apiKey:
        record["api_key"] = request.apiKey
    if request.deployType is not None:
        record["deploy_type"] = request.deployType
    if request.timeout is not None:
        record["timeout"] = request.timeout
    if request.temperature is not None:
        record["temperature"] = request.temperature
    if request.maxTokens is not None:
        record["max_tokens"] = request.maxTokens
    if request.fps is not None:
        record["fps"] = request.fps
    record["updated_at"] = datetime.now(timezone.utc)
    persist_llm_config(record)
    return llm_config_out(record)


@router.delete("/api/llm-configs/{config_id}")
def delete_llm_config(config_id: str) -> dict[str, str]:
    """删除大模型配置：移出内存并删库。"""
    record = state.llm_configs_store.pop(config_id, None)
    if not record:
        raise HTTPException(status_code=404, detail="LLM config not found")
    delete_llm_config_from_db(config_id)
    return {"deleted": config_id}


@router.post("/api/llm-configs/{config_id}/test", response_model=LlmTestResult)
def test_llm_config(config_id: str) -> LlmTestResult:
    """对指定配置发起连接检测（GET {baseUrl}/models）。"""
    record = require_llm_config(config_id)
    return LlmTestResult(**test_llm_connection(record))
