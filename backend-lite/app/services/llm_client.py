"""大模型视觉判定客户端（OpenAI 兼容 chat completions，同步 requests 调用）。"""

import json
import logging
from typing import Any

import requests

from app.utils.assets import jpeg_data_url

logger = logging.getLogger(__name__)

VALID_VERDICTS = ("有效", "无效")
MAX_REASON_CHARS = 500

JUDGE_INSTRUCTION = (
    "请判断图片中是否存在上述目标事件。"
    '只回复 JSON：{"verdict":"有效"或"无效","reason":"简要说明"}，不要输出其他内容。'
)


def _extract_content(data: dict[str, Any]) -> str:
    """从 chat completions 响应中取 choices[0].message.content 文本。

    Args:
        data: 响应 JSON。

    Returns:
        文本内容（list 形态的 content 拼接 text 段）。

    Raises:
        ValueError: 响应结构不符合预期。
    """
    choices = data.get("choices")
    if not choices:
        raise ValueError("LLM response has no choices")
    content = choices[0].get("message", {}).get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [part.get("text", "") for part in content if isinstance(part, dict)]
        return "".join(parts)
    raise ValueError("LLM response message content is missing")


def _parse_verdict(raw: str) -> tuple[str, str]:
    """解析模型输出为 (verdict, reason)；容错 markdown ```json 围栏。

    Args:
        raw: 模型原始输出文本。

    Returns:
        (verdict, reason)：verdict 只能是 有效/无效/空串；解析失败时 verdict 为空串、
        reason 为截断后的原文。
    """
    text = raw.strip()
    if text.startswith("```"):
        # 去掉首行 ```json / ``` 与结尾 ```
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return "", raw[:MAX_REASON_CHARS]
    if not isinstance(data, dict):
        return "", raw[:MAX_REASON_CHARS]
    verdict = str(data.get("verdict") or "")
    if verdict not in VALID_VERDICTS:
        verdict = ""
    reason = str(data.get("reason") or "")
    return verdict, reason[:MAX_REASON_CHARS]


def judge_event(
    *,
    base_url: str,
    api_key: str,
    model: str | None,
    prompt: str,
    image_bytes: bytes,
    timeout: int,
    temperature: float,
    max_tokens: int,
) -> tuple[str, str]:
    """调用 OpenAI 兼容视觉模型判定图片中是否存在目标事件。

    Args:
        base_url: OpenAI 兼容服务 base URL（不含 /chat/completions）。
        api_key: API Key，空串则不带 Authorization 头。
        model: 模型名；None/空串时不在请求中携带 model 字段
            （交由服务端默认模型处理）。
        prompt: 复核类型的判定提示词（作为 system 消息）。
        image_bytes: 待判定图片字节（按 JPEG data URL 上送）。
        timeout: 请求超时秒数。
        temperature: 采样温度。
        max_tokens: 最大输出 token 数。

    Returns:
        (verdict, reason)：verdict 为 有效/无效，解析失败时为空串、reason 为原文截断。

    Raises:
        requests.RequestException: 网络或 HTTP 错误（含 raise_for_status）。
        ValueError: 响应结构不符合预期。
    """
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    payload: dict[str, Any] = {
        "messages": [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": JUDGE_INSTRUCTION},
                    {"type": "image_url", "image_url": {"url": jpeg_data_url(image_bytes)}},
                ],
            },
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if model:
        payload["model"] = model
    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()
    raw = _extract_content(response.json())
    return _parse_verdict(raw)
