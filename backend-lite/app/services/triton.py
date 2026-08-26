"""Triton 模型服务交互与模型注册表状态维护。"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request as UrlRequest
from urllib.request import urlopen
from uuid import uuid4

from fastapi import HTTPException

from app import state
from app.core.config import get_settings
from app.schemas.model import ModelResponse

logger = logging.getLogger(__name__)

TRITON_REQUEST_TIMEOUT_SECONDS = 8


def require_model(model_name: str) -> ModelResponse:
    """按名称取注册模型，不存在则 404。

    Args:
        model_name: 模型名。

    Returns:
        注册表中的模型。

    Raises:
        HTTPException: 模型未注册时 404。
    """
    model = state.model_registry.get(model_name)
    if not model:
        raise HTTPException(status_code=404, detail="Model not registered")
    return model


def refresh_model_states() -> None:
    """从 Triton 拉取模型状态，更新注册表（新模型自动登记）。"""
    try:
        statuses = triton_request("/v2/repository/index", method="POST", payload={"ready": False})
    except HTTPException:
        return
    if not isinstance(statuses, list):
        return
    status_by_name = {item.get("name"): item for item in statuses if isinstance(item, dict) and item.get("name")}
    for name, status in status_by_name.items():
        if name not in state.model_registry:
            now = datetime.now(timezone.utc)
            state.model_registry[name] = ModelResponse(
                id=uuid4(),
                name=name,
                displayName=name,
                repositoryPath=f"/models/{name}",
                modelType="OTHER",
                description=status.get("reason"),
                state=str(status.get("state") or "UNKNOWN"),
                createdAt=now,
                updatedAt=now,
            )
            continue
        new_state = str(status.get("state") or "UNKNOWN")
        if state.model_registry[name].state != new_state:
            update_model_state(name, new_state)


def update_model_state(model_name: str, state_value: str) -> None:
    """更新注册表中模型的状态与更新时间。

    Args:
        model_name: 模型名。
        state_value: Triton 状态字符串。

    Raises:
        HTTPException: 模型未注册时 404。
    """
    model = require_model(model_name)
    state.model_registry[model_name] = model.model_copy(
        update={
            "state": state_value,
            "updatedAt": datetime.now(timezone.utc),
        }
    )


def triton_request(path: str, method: str = "GET", payload: object | None = None) -> object:
    """向 Triton HTTP API 发请求并解析 JSON 响应。

    Args:
        path: API 路径。
        method: HTTP 方法。
        payload: 可选 JSON 请求体。

    Returns:
        解析后的 JSON（空响应返回 {}）。

    Raises:
        HTTPException: Triton 返回错误、不可达或响应非法 JSON 时 502。
    """
    triton_http_url = get_settings().triton_http_url
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = UrlRequest(f"{triton_http_url}{path}", data=body, headers=headers, method=method)  # noqa: S310  # 内网固定 Triton 地址
    try:
        with urlopen(request, timeout=TRITON_REQUEST_TIMEOUT_SECONDS) as response:  # noqa: S310  # 内网固定 Triton 地址
            response_body = response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") or str(exc)
        raise HTTPException(status_code=502, detail=f"Triton request failed: {detail}") from exc
    except URLError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Triton is not reachable at {triton_http_url}: {exc.reason}",
        ) from exc
    if not response_body:
        return {}
    try:
        return json.loads(response_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Triton returned invalid JSON") from exc


def model_config_path(model_name: str) -> Path:
    """解析模型的 config.pbtxt 路径并做目录穿越防护。

    Args:
        model_name: 模型名。

    Returns:
        config.pbtxt 的解析路径。

    Raises:
        HTTPException: 名称非法时 400；配置文件不存在时 404。
    """
    repository = get_settings().triton_model_repository
    safe_name = model_name.strip()
    if not safe_name or safe_name in {".", ".."} or "/" in safe_name or "\\" in safe_name:
        raise HTTPException(status_code=400, detail="Invalid model name")
    config_path = (repository / safe_name / "config.pbtxt").resolve()
    repository_root = repository.resolve()
    if not str(config_path).startswith(str(repository_root)) or not config_path.is_file():
        raise HTTPException(status_code=404, detail=f"Triton model config not found: {safe_name}")
    return config_path


def normalize_gpu_ids(raw_gpu_ids: list[int]) -> list[int]:
    """校验并去重 GPU ID 列表（保持原有顺序）。

    Args:
        raw_gpu_ids: 原始 GPU ID 列表。

    Returns:
        去重后的非负整数列表。

    Raises:
        HTTPException: 含布尔值、非整数、负数或结果为空时 400。
    """
    gpu_ids: list[int] = []
    for raw in raw_gpu_ids:
        if isinstance(raw, bool):
            raise HTTPException(status_code=400, detail="gpuIds must contain non-negative integers")
        try:
            gpu_id = int(raw)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="gpuIds must contain non-negative integers") from exc
        if gpu_id < 0:
            raise HTTPException(status_code=400, detail="gpuIds must contain non-negative integers")
        if gpu_id not in gpu_ids:
            gpu_ids.append(gpu_id)
    if not gpu_ids:
        raise HTTPException(status_code=400, detail="gpuIds must not be empty")
    return gpu_ids


def parse_model_gpu_ids(pbtxt: str) -> list[int]:
    """从 config.pbtxt 文本解析 instance_group 的 gpus 列表。

    Args:
        pbtxt: config.pbtxt 内容。

    Returns:
        GPU ID 列表；无 instance_group 或 gpus 字段时返回空列表。
    """
    group_match = re.search(r"instance_group\s*\[\s*\{(?P<body>.*?)\}\s*\]", pbtxt, flags=re.DOTALL)
    if group_match is None:
        return []
    gpu_match = re.search(r"gpus\s*:\s*\[(?P<ids>[^\]]*)\]", group_match.group("body"))
    if gpu_match is None:
        return []
    gpu_ids: list[int] = []
    for raw in gpu_match.group("ids").split(","):
        value = raw.strip()
        if not value:
            continue
        try:
            gpu_ids.append(int(value))
        except ValueError:
            continue
    return gpu_ids


def update_model_gpu_pbtxt(pbtxt: str, gpu_ids: list[int]) -> str:
    """重写 config.pbtxt 的 instance_group 为指定 GPU 列表。

    Args:
        pbtxt: 原 config.pbtxt 内容。
        gpu_ids: 目标 GPU ID 列表。

    Returns:
        更新后的 pbtxt 文本。
    """
    cleaned = re.sub(
        r"\n?instance_group\s*\[\s*\{.*?\}\s*\]\s*",
        "\n",
        pbtxt.rstrip(),
        flags=re.DOTALL,
    ).rstrip()
    gpu_list = ", ".join(str(gpu_id) for gpu_id in gpu_ids)
    instance_group = f"\ninstance_group [\n  {{\n    kind: KIND_GPU\n    count: 1\n    gpus: [{gpu_list}]\n  }}\n]\n"
    return cleaned + "\n" + instance_group


def reload_triton_model(model_name: str) -> None:
    """卸载并重新加载模型（GPU 配置变更后调用），随后刷新状态。

    Args:
        model_name: 模型名。

    Raises:
        HTTPException: 加载请求失败时 502。
    """
    encoded = quote(model_name, safe="")
    try:
        triton_request(f"/v2/repository/models/{encoded}/unload", method="POST", payload={})
    except HTTPException as exc:
        logger.warning("Triton unload skipped for %s: %s", model_name, exc.detail)
    triton_request(f"/v2/repository/models/{encoded}/load", method="POST", payload={})
    update_model_state(model_name, "LOADING")
    refresh_model_states()
