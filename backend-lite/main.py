"""兼容壳：保留 `uvicorn main:app` 旧启动方式。

实现已全部迁至 app/ 包（装配见 app/main.py），此处仅做 re-export。
"""

from app.main import app

__all__ = ["app"]
