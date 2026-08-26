"""链路追踪：X-Trace-Id 请求头的读取/生成、contextvar 传播与响应回写。"""

import contextvars
import logging
import uuid
from collections.abc import Awaitable, Callable, MutableMapping

from fastapi.responses import JSONResponse

from app.core.exceptions import ErrorCode

logger = logging.getLogger(__name__)

TRACE_ID_HEADER = "X-Trace-Id"

trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="-")


def current_trace_id() -> str:
    """返回当前上下文的 trace_id（无上下文时为 "-"）。"""
    return trace_id_var.get()


class TraceIdMiddleware:
    """纯 ASGI 中间件：trace_id 挂 request.state 与 contextvar，响应头回写。

    采用纯 ASGI 实现（而非 BaseHTTPMiddleware），确保 contextvar 在下游
    路由处理函数与日志记录中可见。
    """

    def __init__(self, app: Callable[..., Awaitable[None]]) -> None:
        self.app = app

    async def __call__(
        self,
        scope: MutableMapping[str, object],
        receive: Callable[..., Awaitable[object]],
        send: Callable[[MutableMapping[str, object]], Awaitable[None]],
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = scope.get("headers") or []
        trace_id = ""
        for name, value in headers:  # type: ignore[union-attr]
            if name.lower() == b"x-trace-id":
                trace_id = value.decode("latin-1")
                break
        if not trace_id:
            trace_id = uuid.uuid4().hex

        state = scope.setdefault("state", {})
        state["trace_id"] = trace_id  # type: ignore[index]
        token = trace_id_var.set(trace_id)

        async def send_with_trace_id(message: MutableMapping[str, object]) -> None:
            if message["type"] == "http.response.start":
                response_headers = message.setdefault("headers", [])
                response_headers.append((b"x-trace-id", trace_id.encode("latin-1")))  # type: ignore[union-attr]
            await send(message)

        try:
            await self.app(scope, receive, send_with_trace_id)
        except Exception as exc:
            # 未捕获异常统一兜底：记录堆栈并返回 500（仅新增 code/traceId 字段）
            logger.exception("unhandled request error: %s", exc)
            response = JSONResponse(
                status_code=500,
                content={
                    "code": ErrorCode.INTERNAL_001,
                    "message": "Internal Server Error",
                    "traceId": trace_id,
                },
            )
            await response(scope, receive, send_with_trace_id)
        finally:
            trace_id_var.reset(token)
