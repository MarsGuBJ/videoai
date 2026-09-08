"""worker 流管理：按摄像头状态与布控任务 reconcile 拉流。"""

import json
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request as UrlRequest
from urllib.request import urlopen
from uuid import UUID

from fastapi import HTTPException

from app import state
from app.core.config import get_settings
from app.schemas.camera import CameraResponse
from app.schemas.deployment_task import DEFAULT_RECOGNITION_PER_MINUTE, DeploymentTaskResponse
from app.services import camera_cache

logger = logging.getLogger(__name__)

WORKER_STREAMS_TIMEOUT_SECONDS = 5
WORKER_REQUEST_TIMEOUT_SECONDS = 10
WORKER_GUARD_INTERVAL_SECONDS = 30


def is_dino_camera(camera: CameraResponse) -> bool:
    """判断摄像头是否属于 DINO 目标检测主机集合。

    Args:
        camera: 摄像头对象。

    Returns:
        sourceUrl 主机命中 VIDEOAI_DINO_CAMERA_HOSTS 时返回 True。
    """
    parsed = urlparse(camera.sourceUrl or "")
    host = parsed.hostname or ""
    return host in get_settings().dino_camera_host_set


def active_face_targets_for_camera(camera: CameraResponse) -> list[dict]:
    """汇总命中该摄像头的运行中人脸布控目标。

    Args:
        camera: 摄像头对象。

    Returns:
        目标字典列表（faceProfileId/deploymentTaskId/recognitionPerMinute）。
    """
    targets: list[dict] = []
    camera_id = str(camera.id)
    for task in state.deployment_tasks_store.values():
        if not task.enabled or task.taskStatus.lower() != "running" or task.faceProfileId is None:
            continue
        if camera_id not in set(task.cameraIds or []):
            continue
        targets.append(
            {
                "faceProfileId": str(task.faceProfileId),
                "deploymentTaskId": str(task.id),
                "recognitionPerMinute": max(1, int(task.recognitionPerMinute or DEFAULT_RECOGNITION_PER_MINUTE)),
            }
        )
    return targets


def active_algorithm_task_for_camera(camera: CameraResponse) -> DeploymentTaskResponse | None:
    """找到命中该摄像头且绑定了算法的运行中布控任务（取第一个）。

    Args:
        camera: 摄像头对象。

    Returns:
        绑定算法的布控任务；无则 None。
    """
    camera_id = str(camera.id)
    for task in state.deployment_tasks_store.values():
        if not task.enabled or task.taskStatus.lower() != "running" or task.algorithmId is None:
            continue
        if camera_id in set(task.cameraIds or []):
            return task
    return None


def algorithm_payload_for_camera(camera: CameraResponse) -> dict | None:
    """组装 worker 启动 payload 的 algorithm 字段（仅当任务绑定算法且版本存在）。

    Args:
        camera: 摄像头对象。

    Returns:
        algorithm payload 字典；无绑定时 None。installPath 为 worker 视角路径
        （backend 与 worker 挂载同一目录，直接按 storage_algorithm_dir/<code>/<version> 拼接）。
    """
    task = active_algorithm_task_for_camera(camera)
    if task is None or task.algorithmId is None:
        return None
    record = state.algorithms_store.get(task.algorithmId)
    if record is None or record.currentVersion is None:
        return None
    install_path = get_settings().storage_algorithm_dir / record.code / record.currentVersion
    return {
        "algorithmId": str(record.id),
        "engineType": record.engineType,
        "version": record.currentVersion,
        "installPath": str(install_path),
        "recognitionPerMinute": max(1, int(task.recognitionPerMinute or DEFAULT_RECOGNITION_PER_MINUTE)),
        "deploymentTaskId": str(task.id),
    }


def should_worker_stream(camera: CameraResponse) -> bool:
    """判断该摄像头是否需要 worker 拉流（DINO、人脸布控目标或绑定算法的任务）。"""
    return (
        is_dino_camera(camera)
        or bool(active_face_targets_for_camera(camera))
        or active_algorithm_task_for_camera(camera) is not None
    )


def sync_worker_streams_for_task(task: DeploymentTaskResponse) -> None:
    """对任务关联的全部摄像头逐个 reconcile worker 流。

    Args:
        task: 布控任务。
    """
    for raw_camera_id in task.cameraIds or []:
        try:
            camera_id = UUID(str(raw_camera_id))
        except ValueError:
            continue
        camera = camera_cache.get(camera_id)
        if camera is not None:
            sync_worker_stream(camera)


def sync_worker_stream(camera: CameraResponse) -> None:
    """按摄像头当前状态启动或停止 worker 流；失败仅记录日志。

    Args:
        camera: 摄像头对象。
    """
    try:
        if camera.status == "RUNNING" and should_worker_stream(camera):
            start_worker_stream(camera)
        else:
            stop_worker_stream(camera.id)
    except HTTPException as exc:
        logger.error("sync_worker_stream failed for %s: %s", camera.streamName, exc.detail)
    except Exception as exc:  # noqa: BLE001  # 单路摄像头失败不得影响其他摄像头的 reconcile
        logger.error("sync_worker_stream failed for %s: %s", camera.streamName, exc)


def start_worker_stream(camera: CameraResponse) -> None:
    """调用 worker 启动一路流。

    Args:
        camera: 摄像头对象。

    Raises:
        HTTPException: worker 不可达或返回错误时 502。
    """
    object_detection_enabled = is_dino_camera(camera)
    face_targets = active_face_targets_for_camera(camera)
    payload = {
        "cameraId": str(camera.id),
        "cameraName": camera.name,
        "streamUrl": worker_stream_url(camera),
        "faceProfileId": face_targets[0]["faceProfileId"] if face_targets else None,
        "deploymentTaskId": face_targets[0]["deploymentTaskId"] if face_targets else None,
        "faceTargets": face_targets,
        "faceDetectionEnabled": bool(face_targets),
        "objectDetectionEnabled": object_detection_enabled,
        "algorithm": algorithm_payload_for_camera(camera),
    }
    worker_request("/v1/streams/start", payload)


def stop_worker_stream(camera_id: UUID) -> None:
    """调用 worker 停止一路流。

    Args:
        camera_id: 摄像头 ID。

    Raises:
        HTTPException: worker 不可达或返回错误时 502。
    """
    worker_request("/v1/streams/stop", {"cameraId": str(camera_id)})


def worker_stream_url(camera: CameraResponse) -> str:
    """计算 worker 实际拉流地址（RTSP 源转 ZLM FLV）。

    Args:
        camera: 摄像头对象。

    Returns:
        拉流 URL。
    """
    if camera.sourceUrl.startswith("rtsp://"):
        return f"{get_settings().srs_http_url}/{camera.streamApp}/{camera.streamName}.live.flv"
    return camera.sourceUrl


def worker_stream_statuses() -> dict[str, str]:
    """查询 worker 当前全部流状态；不可达时返回空表。"""
    worker_url = get_settings().worker_url
    request = UrlRequest(  # noqa: S310  # 内网固定 worker 地址
        f"{worker_url}/v1/streams", headers={"Accept": "application/json"}, method="GET"
    )
    try:
        with urlopen(request, timeout=WORKER_STREAMS_TIMEOUT_SECONDS) as response:  # noqa: S310  # 内网固定 worker 地址
            payload = json.loads(response.read().decode("utf-8"))
        streams = payload.get("streams", {})
        return streams if isinstance(streams, dict) else {}
    except (OSError, ValueError) as exc:  # URLError 属 OSError；JSON 解析失败属 ValueError
        logger.warning("worker stream status unavailable: %s", exc)
        return {}


def worker_request(path: str, payload: object) -> None:
    """向 worker 发送 JSON POST。

    Args:
        path: worker API 路径。
        payload: JSON 请求体。

    Raises:
        HTTPException: worker 返回错误或不可达时 502。
    """
    worker_url = get_settings().worker_url
    body = json.dumps(payload).encode("utf-8")
    request = UrlRequest(  # noqa: S310  # 内网固定 worker 地址
        f"{worker_url}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=WORKER_REQUEST_TIMEOUT_SECONDS):  # noqa: S310  # 内网固定 worker 地址
            return
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") or str(exc)
        raise HTTPException(status_code=502, detail=f"Worker request failed: {detail}") from exc
    except URLError as exc:
        raise HTTPException(status_code=502, detail=f"Worker is not reachable at {worker_url}: {exc.reason}") from exc


def worker_stream_guard_loop() -> None:
    """Periodically reconcile worker streams against the cached camera list."""
    state.worker_guard_stop_event.wait(WORKER_GUARD_INTERVAL_SECONDS)
    while not state.worker_guard_stop_event.is_set():
        try:
            ensure_worker_streams()
        except Exception as exc:  # noqa: BLE001  # 守护线程必须永不退出
            logger.error("worker_stream_guard failed: %s", exc)
        state.worker_guard_stop_event.wait(WORKER_GUARD_INTERVAL_SECONDS)


def ensure_worker_streams() -> None:
    """把 worker 实际流集合对齐到摄像头缓存应有的状态。"""
    statuses = worker_stream_statuses()
    for camera in camera_cache.all():
        if camera.status != "RUNNING" or not should_worker_stream(camera):
            if str(camera.id) in statuses:
                try:
                    stop_worker_stream(camera.id)
                except HTTPException as exc:
                    logger.error("ensure_worker_streams failed to stop %s: %s", camera.streamName, exc.detail)
                except Exception as exc:  # noqa: BLE001  # 单路失败不阻断其余摄像头
                    logger.error("ensure_worker_streams failed to stop %s: %s", camera.streamName, exc)
            continue
        if str(camera.id) in statuses:
            continue
        try:
            start_worker_stream(camera)
        except HTTPException as exc:
            logger.error("ensure_worker_streams failed for %s: %s", camera.streamName, exc.detail)
        except Exception as exc:  # noqa: BLE001  # 单路失败不阻断其余摄像头
            logger.error("ensure_worker_streams failed for %s: %s", camera.streamName, exc)
