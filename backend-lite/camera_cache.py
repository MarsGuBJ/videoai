"""兼容壳：实现已迁至 app/services/camera_cache.py，此处仅 re-export 公共 API。"""

from app.services.camera_cache import all, get, refresh, start, stop

__all__ = ["all", "get", "refresh", "start", "stop"]
