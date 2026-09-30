"""万物核二次复核接口客户端（multipart/form-data 上传，同步 requests 调用）。"""

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

MAX_REASON_CHARS = 500


def _extract_error_detail(response: requests.Response) -> str:
    """从错误响应 JSON 提取 detail（str 或 list）拼成单行文本。

    Args:
        response: 非 2xx 的 HTTP 响应。

    Returns:
        detail 文本；响应非 JSON 或无 detail 字段时返回空串。
    """
    try:
        payload: Any = response.json()
    except ValueError:
        return ""
    detail = payload.get("detail") if isinstance(payload, dict) else None
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        return "; ".join(str(item) for item in detail)
    return ""


def _raise_for_status(response: requests.Response) -> None:
    """非 2xx 时抛 requests.HTTPError，异常信息带上响应 detail 便于排查失败原因。

    Args:
        response: HTTP 响应。

    Raises:
        requests.HTTPError: 状态码 >= 400，信息含提取到的 detail。
    """
    if response.status_code < 400:
        return
    message = f"second-review upload failed with status {response.status_code}"
    detail = _extract_error_detail(response)
    if detail:
        message = f"{message}: {detail}"
    raise requests.HTTPError(message, response=response)


def _parse_result(payload: Any) -> tuple[str, str]:
    """解析万物核响应 body 为 (verdict, reason)。

    Args:
        payload: 响应 JSON（{"code":0,"data":{"result":...,"raw_text":...}} 结构）。

    Returns:
        (verdict, reason)：detected 为 True/False 时 verdict 为 有效/无效；
        result 为 None（未检出结构化结论）时 verdict 为空串、reason 取 raw_text 截断。

    Raises:
        ValueError: 响应结构不符合预期（缺 data 或 result 非对象）。
    """
    if not isinstance(payload, dict):
        raise ValueError("second-review response is not a JSON object")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError("second-review response has no data")
    raw_text = str(data.get("raw_text") or "")
    result = data.get("result")
    if result is None:
        return "", raw_text[:MAX_REASON_CHARS]
    if not isinstance(result, dict):
        raise ValueError("second-review response result is not an object")
    detected = result.get("detected")
    verdict = ""
    if detected is True:
        verdict = "有效"
    elif detected is False:
        verdict = "无效"
    reason = str(result.get("reason") or "") or raw_text
    return verdict, reason[:MAX_REASON_CHARS]


def judge_event(
    *,
    endpoint: str,
    event_type: str,
    prompt: str,
    image_bytes: bytes | None = None,
    video_bytes: bytes | None = None,
    image_name: str = "snapshot.jpg",
    video_name: str = "review-video.mp4",
    event_id: str | None = None,
    timeout: int = 300,
) -> tuple[str, str]:
    """调用万物核二次复核接口判定图片/视频中是否存在目标事件。

    Args:
        endpoint: 万物核服务地址（不含 /api/v1/second-review/upload）。
        event_type: 事件类型（取复核类型名称）。
        prompt: 复核类型的判定提示词。
        image_bytes: 待判定图片字节（必填；视频任务传抽帧缩略图）。
        video_bytes: 待判定视频字节；非空时才上传 video 字段。
        image_name: 图片上传文件名。
        video_name: 视频上传文件名。
        event_id: 事件/任务 ID，可选，供服务端关联留痕。
        timeout: 服务端判定超时秒数（上送 timeout 字段）；requests 客户端超时
            在此基础上加 10 秒兜底。

    Returns:
        (verdict, reason)：verdict 为 有效/无效，未检出结构化结论时为空串、
        reason 为 raw_text 截断。

    Raises:
        ValueError: image_bytes 为空或响应结构不符合预期。
        requests.RequestException: 网络或 HTTP 错误（HTTPError 信息含响应 detail）。
    """
    if not image_bytes:
        raise ValueError("image_bytes is required")
    url = f"{endpoint.rstrip('/')}/api/v1/second-review/upload"
    files: dict[str, tuple[str, bytes]] = {"image": (image_name, image_bytes)}
    if video_bytes:
        files["video"] = (video_name, video_bytes)
    form: dict[str, str] = {
        "event_type": event_type,
        "prompt": prompt,
        "timeout": str(timeout),
    }
    if event_id is not None:
        form["event_id"] = event_id
    response = requests.post(url, files=files, data=form, timeout=timeout + 10)
    _raise_for_status(response)
    return _parse_result(response.json())
