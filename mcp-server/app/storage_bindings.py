"""摄像头 → 录像存储设备（host/username/password）绑定的内存存储与 JSON 落盘。

平台把摄像头"关联"到某台录像存储设备后，该摄像头的录像检索/回放/下载优先使用
绑定的主机与凭据（见 ``nvr_devices.resolve_device_credentials`` 的 ``binding`` 参数）。
启动时从 JSON 文件加载（文件不存在视为空）；写操作先写临时文件再 ``os.replace``
原子落盘，避免半截文件。注意：对外输出（``all()``）绝不包含密码。
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class StorageBindings:
    """摄像头 → 录像存储设备绑定（线程安全，写操作立即落盘）。"""

    def __init__(self, file_path: str) -> None:
        self._file_path = file_path
        self._lock = threading.Lock()
        self._bindings: dict[str, dict[str, str]] = {}
        self._load()

    def _load(self) -> None:
        try:
            raw: Any = json.loads(Path(self._file_path).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return
        except (OSError, json.JSONDecodeError) as exc:
            # 坏文件视为空，不阻塞服务启动；运维可修复后重新绑定
            logger.warning(
                "storage bindings file %s unreadable, starting empty: %s", self._file_path, type(exc).__name__
            )
            return
        if not isinstance(raw, dict):
            logger.warning("storage bindings file %s is not a JSON object, starting empty", self._file_path)
            return
        self._bindings = {
            str(camera_id): {
                "host": str(item.get("host") or ""),
                "username": str(item.get("username") or ""),
                "password": str(item.get("password") or ""),
            }
            for camera_id, item in raw.items()
            if isinstance(item, dict)
        }

    def all(self) -> list[dict[str, str]]:
        """返回全部绑定的对外视图（cameraId/host/username），不含密码。"""
        with self._lock:
            return [
                {"cameraId": camera_id, "host": binding["host"], "username": binding["username"]}
                for camera_id, binding in self._bindings.items()
            ]

    def get(self, camera_id: str) -> dict[str, str] | None:
        """返回摄像头的完整绑定（含密码，仅供内部解析设备凭据用）；未绑定返回 None。"""
        with self._lock:
            binding = self._bindings.get(camera_id)
            return dict(binding) if binding is not None else None

    def bind(self, items: list[dict[str, str]]) -> int:
        """批量绑定/覆盖（同 cameraId 覆盖），返回写入条数。"""
        with self._lock:
            for item in items:
                self._bindings[str(item["cameraId"])] = {
                    "host": str(item["host"]),
                    "username": str(item["username"]),
                    "password": str(item["password"]),
                }
            self._save_locked()
            return len(items)

    def unbind(self, camera_ids: list[str]) -> int:
        """批量解绑，返回实际移除的条数。"""
        with self._lock:
            removed = 0
            for camera_id in camera_ids:
                if self._bindings.pop(camera_id, None) is not None:
                    removed += 1
            if removed:
                self._save_locked()
            return removed

    def _save_locked(self) -> None:
        # 先写临时文件再 os.replace 原子替换，避免进程中断留下半截 JSON
        directory = os.path.dirname(self._file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        tmp_path = f"{self._file_path}.tmp"
        Path(tmp_path).write_text(
            json.dumps(self._bindings, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(tmp_path, self._file_path)
