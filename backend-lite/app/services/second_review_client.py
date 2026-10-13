"""万物核二次复核接口客户端（multipart/form-data 上传，同步 requests 调用）。"""

import json
import logging
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger(__name__)

MAX_REASON_CHARS = 500


@dataclass
class JudgeResult:
    """万物核判定结果：结论、原因、耗时、置信度与判断依据。"""

    verdict: str
    reason: str
    elapsed_seconds: float | None = None
    confidence: float | None = None
    evidence: str = ""


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


def _to_float(value: Any) -> float | None:
    """把响应里的数值字段转成 float；非数值或缺失时返回 None。"""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def parse_bbox_text(value: str) -> list[list[float]] | None:
    """把用户录入的 bbox 坐标文本解析为 [[x1,y1,x2,y2], ...]。

    Args:
        value: 复核类型配置的 bbox 坐标文本（JSON 数组格式）。

    Returns:
        解析后的坐标列表；文本非法或为空列表时返回 None（调用方回退处理）。
    """
    try:
        parsed: Any = json.loads(value)
    except ValueError:
        return None
    if not isinstance(parsed, list) or not parsed:
        return None
    bbox: list[list[float]] = []
    for item in parsed:
        if not isinstance(item, (list, tuple)) or len(item) != 4:
            return None
        try:
            bbox.append([float(coord) for coord in item])
        except (TypeError, ValueError):
            return None
    return bbox


def _serialize_evidence(value: Any) -> str:
    """evidence 字段归一化为文本：list/dict 转 JSON 字符串，其余转 str。"""
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _parse_result(payload: Any) -> JudgeResult:
    """解析万物核响应 body 为判定结果。

    Args:
        payload: 响应 JSON（{"code":0,"data":{"elapsed_seconds":...,"result":...,"raw_text":...}} 结构）。

    Returns:
        JudgeResult：detected 为 True/False 时 verdict 为 有效/无效；
        result 为 None（未检出结构化结论）时 verdict 为空串、reason 取 raw_text 截断；
        elapsed_seconds 取 data 层字段，confidence / evidence 取 result 层字段。

    Raises:
        ValueError: 响应结构不符合预期（缺 data 或 result 非对象）。
    """
    if not isinstance(payload, dict):
        raise ValueError("second-review response is not a JSON object")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError("second-review response has no data")
    raw_text = str(data.get("raw_text") or "")
    elapsed_seconds = _to_float(data.get("elapsed_seconds"))
    result = data.get("result")
    if result is None:
        return JudgeResult(verdict="", reason=raw_text[:MAX_REASON_CHARS], elapsed_seconds=elapsed_seconds)
    if not isinstance(result, dict):
        raise ValueError("second-review response result is not an object")
    detected = result.get("detected")
    verdict = ""
    if detected is True:
        verdict = "有效"
    elif detected is False:
        verdict = "无效"
    reason = str(result.get("reason") or "") or raw_text
    return JudgeResult(
        verdict=verdict,
        reason=reason[:MAX_REASON_CHARS],
        elapsed_seconds=elapsed_seconds,
        confidence=_to_float(result.get("confidence")),
        evidence=_serialize_evidence(result.get("evidence")),
    )


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
    bbox: list[Any] | None = None,
    roi: str | None = None,
    timeout: int = 300,
) -> JudgeResult:
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
        bbox: 识别对象坐标（[[x1,y1,x2,y2], ...]），非空时以 JSON 字符串上送 bbox 字段。
        roi: 电子围栏 ROI 区域坐标文本，非空时原样上送 roi 字段。
        timeout: 服务端判定超时秒数（上送 timeout 字段）；requests 客户端超时
            在此基础上加 10 秒兜底。

    Returns:
        JudgeResult：verdict 为 有效/无效，未检出结构化结论时为空串、
        reason 为 raw_text 截断；elapsed_seconds / confidence / evidence
        分别对应接口返回的 data.elapsed_seconds、data.result.confidence、
        data.result.evidence，缺失时为 None / 空串。

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
    if bbox:
        form["bbox"] = json.dumps(bbox, ensure_ascii=False)
    if roi:
        form["roi"] = roi
    response = requests.post(url, files=files, data=form, timeout=timeout + 10)
    _raise_for_status(response)
    return _parse_result(response.json())
