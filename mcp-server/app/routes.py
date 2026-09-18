"""HTTP wrapper routes that expose each MCP tool as a POST endpoint."""

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from inspect import Parameter, signature
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from .context import channel_lookup, hcnetsdk_playback, known_nvr_hosts, mcp, nvr_devices, videoai
from .nvr_devices import resolve_device_credentials
from .tools import (
    detect_persons,
    detect_persons_with_id,
    dino_events,
    download_recording,
    export_recording,
    gait_feature_compare,
    gait_feature_extract_and_insert,
    get_live_stream,
    get_person_bbox,
    get_person_search_result,
    list_cameras,
    query_face_matches,
    search_person_by_bbox,
    search_person_by_image,
    search_recordings,
    text_search_images,
    upload_face_image,
    video_understanding,
)

logger = logging.getLogger(__name__)

# 浏览器播放器（mpegts.js fetch）跨源直连 /recording-live（前端 5173 -> MCP 8097 -> ZLM :82），
# 302 与错误响应都必须带 CORS 头，否则浏览器在跳转第一跳就拦截
RECORDING_LIVE_CORS_HEADERS = {"Access-Control-Allow-Origin": "*"}


def register_http_tool_routes() -> None:
    tool_handlers = {
        "list_cameras": list_cameras,
        "get_live_stream": get_live_stream,
        "search_recordings": search_recordings,
        "download_recording": download_recording,
        "export_recording": export_recording,
        "video_understanding": video_understanding,
        "upload_face_image": upload_face_image,
        "query_face_matches": query_face_matches,
        "detect_persons": detect_persons,
        "search_person_by_bbox": search_person_by_bbox,
        "get_person_search_result": get_person_search_result,
        "detect_persons_with_id": detect_persons_with_id,
        "get_person_bbox": get_person_bbox,
        "gait_feature_compare": gait_feature_compare,
        "gait_feature_extract_and_insert": gait_feature_extract_and_insert,
        "dino_events": dino_events,
        "text_search_images": text_search_images,
        "search_person_by_image": search_person_by_image,
    }
    for tool_name, handler in tool_handlers.items():
        register_http_tool_route(tool_name, handler)
    register_recording_live_route()


def parse_playback_speed(raw: str) -> float:
    """解析回放倍速参数；缺省 1.0，仅支持现场 NVR 实测档位（PLAYBACK_SPEEDS）。"""
    from .tools.recordings import PLAYBACK_SPEEDS  # 避免模块加载期循环依赖

    if not raw.strip():
        return 1.0
    try:
        speed = float(raw)
    except ValueError:
        raise ValueError(f"unsupported playback speed: {raw}; supported: {PLAYBACK_SPEEDS}") from None
    if speed not in PLAYBACK_SPEEDS:
        raise ValueError(f"unsupported playback speed: {speed}; supported: {PLAYBACK_SPEEDS}")
    return speed


def register_recording_live_route() -> None:
    from .tools.recordings import parse_datetime  # 避免模块加载期循环依赖

    @mcp.custom_route("/recording-live", methods=["GET"], name="recording_live")
    async def recording_live_endpoint(request: Request) -> JSONResponse | RedirectResponse:
        """按需建立录像回放流：按 startTime/endTime 临时创建 SDK 回放，302 到 ZLM FLV 地址。

        带 cameraId 时按摄像头定位其 NVR（与检索/下载同一套 resolve_device_credentials 解析：
        sourceUrl 直连 IPC 时反查所属 NVR 与实际通道）建立回放，并补偿设备时钟偏差；
        NVR 回放并发数受限时逐出最早建立的会话，保证新请求总能拿到流。
        speed 为可选回放倍速（0.25/0.5/1/2/4/8/16/32，默认 1）。
        """
        try:
            start = parse_datetime(request.query_params.get("startTime", ""))
            end = parse_datetime(request.query_params.get("endTime", ""))
            if end <= start:
                raise ValueError("endTime must be later than startTime")
            speed = parse_playback_speed(request.query_params.get("speed", ""))
            camera_id = request.query_params.get("cameraId", "").strip()
            if camera_id:
                camera = await videoai.get_camera(camera_id)
                # 与录像检索/下载走同一套解析：sourceUrl 直连 IPC 时反查所属 NVR，
                # 否则会把回放打到 IPC 自己身上（录像存在 NVR 上）而起流失败
                credentials = await resolve_device_credentials(camera, channel_lookup, known_nvr_hosts)
                proxy = nvr_devices.proxy_for_credentials(credentials)
                # 设备时钟偏差补偿：SDK 回放时间按设备本地时钟解释
                shift = timedelta(seconds=await proxy.measure_clock_skew())
                recording = proxy.build_recording(start + shift, end + shift, credentials.channel)
            else:
                proxy = hcnetsdk_playback
                recording = proxy.build_recording(start, end)
            url = await proxy.ensure_playback(recording, speed)
            return RedirectResponse(url, status_code=302, headers=RECORDING_LIVE_CORS_HEADERS)
        except ValueError as exc:
            return JSONResponse(error_payload("ValueError", str(exc)), status_code=400, headers=RECORDING_LIVE_CORS_HEADERS)
        except Exception as exc:  # noqa: BLE001  # 兜底：与 -http 接口一致，细节只进服务端日志
            logger.exception("recording-live failed with %s", type(exc).__name__)
            return JSONResponse(error_payload(type(exc).__name__, "internal server error"), status_code=500, headers=RECORDING_LIVE_CORS_HEADERS)


def register_http_tool_route(tool_name: str, handler: Callable[..., Awaitable[dict]]) -> None:
    @mcp.custom_route(f"/{tool_name}-http", methods=["POST"], name=f"{tool_name}_http")
    async def http_tool_endpoint(request: Request, _handler=handler) -> JSONResponse:
        try:
            arguments = await parse_http_arguments(request, _handler)
            result = await _handler(**arguments)
            return JSONResponse(json_safe(result))
        except ValueError as exc:
            return JSONResponse(error_payload("ValueError", str(exc)), status_code=400)
        except Exception as exc:  # noqa: BLE001  # 兜底：任何未预期异常统一返回 500 与通用错误信息
            logger.exception("http tool %s failed with %s", tool_name, type(exc).__name__)
            return JSONResponse(error_payload(type(exc).__name__, "internal server error"), status_code=500)


async def parse_http_arguments(request: Request, handler: Callable[..., Awaitable[dict]]) -> dict[str, Any]:
    payload = await read_json_object(request)
    params = {
        name: param
        for name, param in signature(handler).parameters.items()
        if param.kind in {Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY}
    }
    unknown = sorted(set(payload) - set(params))
    if unknown:
        raise ValueError(f"unknown parameter(s): {', '.join(unknown)}")
    missing = sorted(name for name, param in params.items() if param.default is Parameter.empty and name not in payload)
    if missing:
        raise ValueError(f"missing required parameter(s): {', '.join(missing)}")
    return {name: convert_http_argument(name, value, params[name].annotation) for name, value in payload.items()}


async def read_json_object(request: Request) -> dict[str, Any]:
    body = await request.body()
    if not body:
        return {}
    try:
        payload = await request.json()
    except Exception as exc:  # noqa: BLE001  # JSON 解析失败的异常类型取决于底层库，统一改写为 400
        raise ValueError("request body must be a JSON object") from exc
    if not isinstance(payload, dict):
        raise ValueError("request body must be a JSON object")
    return payload


def convert_http_argument(name: str, value: Any, annotation: Any) -> Any:
    if annotation is bool:
        return convert_http_bool(name, value)
    if annotation is int:
        return convert_http_int(name, value)
    if annotation is float:
        return convert_http_float(name, value)
    if annotation is str:
        if value is None:
            return ""
        return value if isinstance(value, str) else str(value)
    return value


def convert_http_bool(name: str, value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "on"}:
            return True
        if normalized in {"false", "0", "no", "n", "off"}:
            return False
    raise ValueError(f"{name} must be a boolean")


def convert_http_int(name: str, value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc


def convert_http_float(name: str, value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "model_dump"):
        return json_safe(value.model_dump(mode="json"))
    return value


def error_payload(error_type: str, message: str) -> dict:
    return {"error": {"type": error_type, "message": message}}
