"""大模型配置的内存态、数据库持久化与连接检测。"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, cast

import requests
from fastapi import HTTPException
from sqlalchemy import Table, text
from sqlalchemy.exc import SQLAlchemyError

from app import state
from app.db.session import SessionLocal, engine
from app.models.llm_config import LlmConfigORM
from app.schemas.llm_config import LlmConfigOut

logger = logging.getLogger(__name__)


def require_llm_config(config_id: str) -> dict[str, Any]:
    """按 ID 取大模型配置，不存在则 404。

    Args:
        config_id: 配置 ID。

    Returns:
        内存态中的配置字典。

    Raises:
        HTTPException: 配置不存在时 404。
    """
    record = state.llm_configs_store.get(config_id)
    if not record:
        raise HTTPException(status_code=404, detail="LLM config not found")
    return record


def mask_api_key(api_key: str) -> str:
    """apiKey 掩码：仅保留前 3 字符 + "***"（空串原样返回）。

    Args:
        api_key: 明文 API Key。

    Returns:
        掩码后的字符串。
    """
    if not api_key:
        return ""
    return api_key[:3] + "***"


def llm_config_out(record: dict[str, Any]) -> LlmConfigOut:
    """把内存态配置字典转为对外 DTO（apiKey 掩码）。

    Args:
        record: 内存态配置字典。

    Returns:
        camelCase 对外 DTO。
    """
    api_key = str(record.get("api_key") or "")
    return LlmConfigOut(
        id=str(record["id"]),
        name=str(record["name"]),
        baseUrl=str(record["base_url"]),
        model=str(record.get("model") or ""),
        apiKey=mask_api_key(api_key),
        apiKeyConfigured=bool(api_key),
        deployType=str(record["deploy_type"]),  # type: ignore[arg-type]
        timeout=int(record["timeout"]),
        temperature=float(record["temperature"]),
        maxTokens=int(record["max_tokens"]),
        fps=int(record["fps"]),
        createdAt=record["created_at"],
        updatedAt=record["updated_at"],
    )


def ensure_llm_config_schema() -> None:
    """轻量迁移：确保 llm_configs 表存在并补列（幂等，容错不阻断启动）。"""
    try:
        with engine.begin() as conn:
            cast(Table, LlmConfigORM.__table__).create(conn, checkfirst=True)
            conn.execute(
                text("ALTER TABLE llm_configs ADD COLUMN IF NOT EXISTS model VARCHAR(200)")
            )
    except SQLAlchemyError as exc:  # 数据库不可达时跳过迁移，不阻断启动
        logger.error("llm config schema ensure failed: %s", exc)


def load_llm_configs_from_db() -> None:
    """启动时把数据库中的大模型配置载入内存存储。"""
    try:
        with SessionLocal() as pgdb:
            rows = pgdb.query(LlmConfigORM).all()
            state.llm_configs_store.clear()
            for row in rows:
                state.llm_configs_store[str(row.id)] = {
                    "id": str(row.id),
                    "name": row.name,
                    "base_url": row.base_url,
                    "model": row.model or "",
                    "api_key": row.api_key or "",
                    "deploy_type": row.deploy_type,
                    "timeout": int(row.timeout or 30),
                    "temperature": float(row.temperature),
                    "max_tokens": int(row.max_tokens),
                    "fps": int(row.fps),
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                }
    except SQLAlchemyError as exc:  # 数据库不可达时以空配置集启动（与布控任务一致）
        logger.error("llm config load failed: %s", exc)


def persist_llm_config(record: dict[str, Any]) -> None:
    """把配置 upsert 到数据库；失败仅记录日志，不影响内存态。

    Args:
        record: 待持久化的配置字典。
    """
    try:
        with SessionLocal() as pgdb:
            row = pgdb.get(LlmConfigORM, str(record["id"]))
            if row is None:
                row = LlmConfigORM(id=str(record["id"]))
                pgdb.add(row)
            row.name = str(record["name"])
            row.base_url = str(record["base_url"])
            row.model = str(record.get("model") or "")
            row.api_key = str(record.get("api_key") or "")
            row.deploy_type = str(record["deploy_type"])
            row.timeout = int(record["timeout"])
            row.temperature = float(record["temperature"])
            row.max_tokens = int(record["max_tokens"])
            row.fps = int(record["fps"])
            row.created_at = record["created_at"]
            row.updated_at = record["updated_at"]
            pgdb.commit()
    except SQLAlchemyError as exc:
        logger.error("llm config persist failed: %s", exc)


def delete_llm_config_from_db(config_id: str) -> None:
    """从数据库删除配置；失败仅记录日志。

    Args:
        config_id: 配置 ID。
    """
    try:
        with SessionLocal() as pgdb:
            row = pgdb.get(LlmConfigORM, config_id)
            if row is not None:
                pgdb.delete(row)
                pgdb.commit()
    except SQLAlchemyError as exc:
        logger.error("llm config delete failed: %s", exc)


def test_llm_connection(cfg: dict[str, Any]) -> dict[str, Any]:
    """检测大模型服务连通性：GET {baseUrl}/models（OpenAI 兼容端点）。

    Args:
        cfg: 配置字典，读取 base_url / api_key / timeout。

    Returns:
        与 LlmTestResult 对齐的字典（ok / latencyMs / statusCode / error / checkedAt）。
    """
    checked_at = datetime.now(timezone.utc)
    base_url = str(cfg.get("base_url") or "").rstrip("/")
    api_key = str(cfg.get("api_key") or "")
    timeout = int(cfg.get("timeout") or 30)
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    started = time.perf_counter()
    try:
        response = requests.get(f"{base_url}/models", headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        return {
            "ok": False,
            "latencyMs": None,
            "statusCode": None,
            "error": f"{type(exc).__name__}: {exc}",
            "checkedAt": checked_at,
        }
    latency_ms = int((time.perf_counter() - started) * 1000)
    if 200 <= response.status_code < 300:
        return {
            "ok": True,
            "latencyMs": latency_ms,
            "statusCode": response.status_code,
            "error": None,
            "checkedAt": checked_at,
        }
    return {
        "ok": False,
        "latencyMs": latency_ms,
        "statusCode": response.status_code,
        "error": f"HTTP {response.status_code}",
        "checkedAt": checked_at,
    }
