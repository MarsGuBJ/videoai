"""HTTP wrapper routes that expose each MCP tool as a POST endpoint."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from inspect import Parameter, signature
from typing import Any
from urllib.parse import unquote, urlparse

from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from .context import (
    channel_lookup,
    hcnetsdk_live,
    hcnetsdk_playback,
    known_nvr_hosts,
    mcp,
    nvr_devices,
    storage_bindings,
    stream_id_mappings,
    videoai,
)
from .nvr_devices import (
    STREAM_ID_MAPPED_LABEL,
    effective_storage_host,
    resolve_device_credentials,
    verify_storage_recording,
)
from .tools import (
    detect_persons,
    dino_events,
    download_recording,
    export_recording,
    gait_feature_compare,
    gait_feature_extract_and_insert,
    get_live_stream,
    get_person_search_result,
    # get_recording_stream 只暴露 HTTP 兼容接口，未注册为 MCP tool（见 tools/recordings.py）
    get_recording_stream,
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
        # HTTP 兼容接口：返回 H.265 直通回放流；刻意不注册为 MCP tool
        "get_recording_stream": get_recording_stream,
        "download_recording": download_recording,
        "export_recording": export_recording,
        "video_understanding": video_understanding,
        "upload_face_image": upload_face_image,
        "query_face_matches": query_face_matches,
        "detect_persons": detect_persons,
        "search_person_by_bbox": search_person_by_bbox,
        "get_person_search_result": get_person_search_result,
        "gait_feature_compare": gait_feature_compare,
        "gait_feature_extract_and_insert": gait_feature_extract_and_insert,
        "dino_events": dino_events,
        "text_search_images": text_search_images,
        "search_person_by_image": search_person_by_image,
    }
    for tool_name, handler in tool_handlers.items():
        register_http_tool_route(tool_name, handler)
    register_recording_live_route()
    register_storage_binding_routes()
    register_stream_id_mapping_routes()
    register_live_pull_routes()


def register_stream_id_mapping_routes() -> None:
    """摄像头 IP→非ISAPI CVR 流ID映射的查询/导入 HTTP 接口（平台侧调用）。"""

    @mcp.custom_route("/stream-id-mappings", methods=["GET"], name="stream_id_mappings_list")
    async def list_stream_id_mappings(request: Request) -> JSONResponse:
        # 对外视图不含密码
        return JSONResponse({"data": stream_id_mappings.all()})

    @mcp.custom_route("/stream-id-mappings/import", methods=["POST"], name="stream_id_mappings_import")
    async def import_stream_id_mappings(request: Request) -> JSONResponse:
        """批量导入流ID映射（同 cameraHost 覆盖），校验不通过的行跳过并返回原因。

        请求体：{"rows": [{"streamId", "cameraHost"}], "cvr": {"host", "port"=8000,
        "username", "password"}}；cvr 对整批生效。streamId 去除 * 与空白后必须非空、
        cameraHost 必须是合法 IPv4、cvr.host 必须非空，不满足的行进入 skipped。
        """
        try:
            payload = await read_json_object(request)
            rows = payload.get("rows")
            if not isinstance(rows, list):
                raise ValueError("rows must be a list")
            cvr = payload.get("cvr")
            if not isinstance(cvr, dict):
                raise ValueError("cvr must be an object")
            return JSONResponse({"data": stream_id_mappings.import_rows(rows, cvr)})
        except ValueError as exc:
            return JSONResponse(error_payload("ValueError", str(exc)), status_code=400)
        except Exception as exc:  # noqa: BLE001  # 兜底：与 -http 接口一致，细节只进服务端日志
            logger.exception("stream-id-mappings/import failed with %s", type(exc).__name__)
            return JSONResponse(error_payload(type(exc).__name__, "internal server error"), status_code=500)


def register_storage_binding_routes() -> None:
    """摄像头→录像存储设备绑定的查询/绑定/解绑 HTTP 接口（平台侧调用）。"""

    @mcp.custom_route("/storage-bindings", methods=["GET"], name="storage_bindings_list")
    async def list_storage_bindings(request: Request) -> JSONResponse:
        # 对外视图不含密码
        return JSONResponse({"data": storage_bindings.all()})

    @mcp.custom_route("/storage-bindings/resolved", methods=["GET"], name="storage_bindings_resolved")
    async def list_resolved_storage_bindings(request: Request) -> JSONResponse:
        """各摄像头实际生效的录像存储设备（显式绑定 > sourceUrl 已知设备 > 反查命中）。

        供平台"录像存储配置"展示：设备大多数并非显式绑定，而是回放链路按
        ``effective_storage_host`` 解析出的 NVR/CVR。``bound`` 标记是否为显式绑定
        （只有显式绑定可通过 unbind 解除）。无显式绑定但命中流ID映射的摄像头
        host 为 ``流ID映射`` 且带 ``streamIdMapped: true``。
        """
        try:
            cameras = await videoai.list_cameras()
            data = []
            for camera in cameras:
                binding = storage_bindings.get(camera.id)
                host = await effective_storage_host(
                    camera, channel_lookup, known_nvr_hosts, binding=binding, stream_id_mappings=stream_id_mappings
                )
                if host:
                    entry = {"cameraId": camera.id, "host": host, "bound": binding is not None}
                    if host == STREAM_ID_MAPPED_LABEL:
                        entry["streamIdMapped"] = True
                    data.append(entry)
            return JSONResponse({"data": data})
        except Exception as exc:  # noqa: BLE001  # 兜底：与 -http 接口一致，细节只进服务端日志
            logger.exception("storage-bindings/resolved failed with %s", type(exc).__name__)
            return JSONResponse(error_payload(type(exc).__name__, "internal server error"), status_code=500)

    @mcp.custom_route("/storage-bindings/bind", methods=["POST"], name="storage_bindings_bind")
    async def bind_storage(request: Request) -> JSONResponse:
        """绑定前逐台校验：存储设备上查得到该摄像头录像的才真正绑定，其余跳过并返回原因。

        避免把摄像头关联到错误的存储设备上（设备选错时通道反查不命中，或有通道但
        该通道近期无录像）。响应 data 含 ``bound``（实际绑定数）与 ``skipped``
        （跳过的 cameraId 及原因），校验并发执行。
        """
        try:
            payload = await read_json_object(request)
            items = payload.get("items")
            if not isinstance(items, list):
                raise ValueError("items must be a list")
            for item in items:
                if not isinstance(item, dict) or not all(
                    str(item.get(key) or "").strip() for key in ("cameraId", "host", "username", "password")
                ):
                    raise ValueError("each item must have non-empty cameraId/host/username/password")
            cameras = {camera.id: camera for camera in await videoai.list_cameras()}

            async def verify(item: dict) -> tuple[dict, str | None]:
                camera = cameras.get(str(item["cameraId"]))
                if camera is None:
                    return item, "摄像头不存在或已删除"
                # 绑定带流ID时映射即权威（来自 CVR 流源导出），跳过 ISAPI 校验直接绑定；
                # 这类设备（现场 DS-A CVR）ISAPI 关闭，校验必然失败
                if str(item.get("streamId") or "").strip():
                    return item, None
                reason = await verify_storage_recording(
                    camera,
                    str(item["host"]).strip(),
                    str(item["username"]).strip(),
                    str(item["password"]),
                )
                return item, reason

            results = await asyncio.gather(*(verify(item) for item in items))
            verified = [item for item, reason in results if reason is None]
            skipped = [
                {"cameraId": str(item["cameraId"]), "reason": reason}
                for item, reason in results
                if reason is not None
            ]
            bound = storage_bindings.bind(verified) if verified else 0
            return JSONResponse({"data": {"bound": bound, "skipped": skipped}})
        except ValueError as exc:
            return JSONResponse(error_payload("ValueError", str(exc)), status_code=400)
        except Exception as exc:  # noqa: BLE001  # 兜底：与 -http 接口一致，细节只进服务端日志
            logger.exception("storage-bindings/bind failed with %s", type(exc).__name__)
            return JSONResponse(error_payload(type(exc).__name__, "internal server error"), status_code=500)

    @mcp.custom_route("/storage-bindings/unbind", methods=["POST"], name="storage_bindings_unbind")
    async def unbind_storage(request: Request) -> JSONResponse:
        try:
            payload = await read_json_object(request)
            camera_ids = payload.get("cameraIds")
            if not isinstance(camera_ids, list) or not all(isinstance(item, str) for item in camera_ids):
                raise ValueError("cameraIds must be a list of strings")
            return JSONResponse({"data": {"unbound": storage_bindings.unbind(camera_ids)}})
        except ValueError as exc:
            return JSONResponse(error_payload("ValueError", str(exc)), status_code=400)
        except Exception as exc:  # noqa: BLE001  # 兜底：与 -http 接口一致，细节只进服务端日志
            logger.exception("storage-bindings/unbind failed with %s", type(exc).__name__)
            return JSONResponse(error_payload(type(exc).__name__, "internal server error"), status_code=500)


def register_live_pull_routes() -> None:
    """RTSP 不可用海康设备的 SDK 实时拉流（平台开播兜底，见 hcnetsdk_live）。"""

    @mcp.custom_route("/live-pull/start", methods=["POST"], name="live_pull_start")
    async def live_pull_start(request: Request) -> JSONResponse:
        try:
            payload = await read_json_object(request)
            stream_name = str(payload.get("streamName") or "").strip()
            source_url = str(payload.get("sourceUrl") or "").strip()
            if not stream_name or not source_url:
                raise ValueError("streamName and sourceUrl are required")
            parsed = urlparse(source_url)
            if parsed.scheme not in ("rtsp", "rtsps") or not parsed.hostname:
                raise ValueError("sourceUrl must be an rtsp URL")
            username = unquote(parsed.username or "")
            password = unquote(parsed.password or "")
            if not username:
                raise ValueError("sourceUrl must carry credentials")
            sdk_port = int(payload.get("sdkPort") or 8000)
            stream_type = str(payload.get("streamType") or "main")
            await hcnetsdk_live.start(
                stream_name=stream_name,
                host=parsed.hostname,
                port=sdk_port,
                username=username,
                password=password,
                stream_type=stream_type,
            )
            return JSONResponse({"data": {"streamName": stream_name, "pushed": True}})
        except ValueError as exc:
            return JSONResponse(error_payload("ValueError", str(exc)), status_code=400)
        except Exception as exc:  # noqa: BLE001  # 兜底：与 -http 接口一致，细节只进服务端日志
            logger.exception("live-pull/start failed with %s", type(exc).__name__)
            return JSONResponse(error_payload(type(exc).__name__, str(exc)), status_code=502)

    @mcp.custom_route("/live-pull/stop", methods=["POST"], name="live_pull_stop")
    async def live_pull_stop(request: Request) -> JSONResponse:
        try:
            payload = await read_json_object(request)
            stream_name = str(payload.get("streamName") or "").strip()
            if not stream_name:
                raise ValueError("streamName is required")
            await hcnetsdk_live.stop(stream_name)
            return JSONResponse({"data": {"streamName": stream_name, "stopped": True}})
        except ValueError as exc:
            return JSONResponse(error_payload("ValueError", str(exc)), status_code=400)
        except Exception as exc:  # noqa: BLE001
            logger.exception("live-pull/stop failed with %s", type(exc).__name__)
            return JSONResponse(error_payload(type(exc).__name__, "internal server error"), status_code=500)


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
                credentials = await resolve_device_credentials(
                    camera,
                    channel_lookup,
                    known_nvr_hosts,
                    binding=storage_bindings.get(camera.id),
                    stream_id_mappings=stream_id_mappings,
                )
                proxy = nvr_devices.proxy_for_credentials(credentials)
                # 设备时钟偏差补偿：SDK 回放时间按设备本地时钟解释
                shift = timedelta(seconds=await proxy.measure_clock_skew())
                recording = proxy.build_recording(
                    start + shift, end + shift, credentials.channel or None, stream_id=credentials.stream_id
                )
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
