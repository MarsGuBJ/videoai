"""统一日志配置：默认文本格式含 trace_id；LOG_JSON=true 时输出 JSON 行。"""

import json
import logging
from datetime import datetime, timezone

from app.core.config import get_settings
from app.core.trace import current_trace_id

DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] [trace_id=%(trace_id)s] %(message)s"


class _TraceIdFilter(logging.Filter):
    """为每条记录注入当前 trace_id（无上下文时为 "-"）。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = current_trace_id()
        return True


class JsonFormatter(logging.Formatter):
    """最小 JSON 行格式日志（避免引入第三方依赖）。"""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "trace_id": getattr(record, "trace_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: int = logging.INFO) -> None:
    """初始化 root logger：注入 trace_id filter，按配置切换文本/JSON 格式。

    Args:
        level: root logger 级别，默认 INFO。
    """
    settings = get_settings()
    handler = logging.StreamHandler()
    if settings.log_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(settings.log_format or DEFAULT_LOG_FORMAT))
    handler.addFilter(_TraceIdFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
