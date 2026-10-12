"""摄像头 IP → 非ISAPI CVR 设备流ID映射的内存存储与 JSON 落盘。

现场部分 CVR（非ISAPI）设备的录像只能按流ID回放：平台导出 CVR 流源清单后，按
``摄像头IP → {streamId, cvrHost, cvrPort, username, password}`` 批量导入。
摄像头既无显式存储绑定、又无法从 sourceUrl/NVR 反查解析出录像设备凭据时，
``nvr_devices.resolve_device_credentials`` 回退到本映射，按流ID直接从 CVR 起播。
启动时从 JSON 文件加载（文件不存在视为空）；写操作先写临时文件再 ``os.replace``
原子落盘，避免半截文件。注意：对外输出（``all()``）绝不包含密码。
"""

from __future__ import annotations

import json
import logging
import os
import threading
from ipaddress import IPv4Address, ip_address
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_CVR_PORT = 8000


class StreamIdMappings:
    """摄像头 IP → 流ID映射（线程安全，写操作立即落盘）。"""

    def __init__(self, file_path: str) -> None:
        self._file_path = file_path
        self._lock = threading.Lock()
        self._mappings: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        try:
            raw: Any = json.loads(Path(self._file_path).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return
        except (OSError, json.JSONDecodeError) as exc:
            # 坏文件视为空，不阻塞服务启动；运维可修复后重新导入
            logger.warning(
                "stream id mappings file %s unreadable, starting empty: %s", self._file_path, type(exc).__name__
            )
            return
        if not isinstance(raw, dict):
            logger.warning("stream id mappings file %s is not a JSON object, starting empty", self._file_path)
            return
        self._mappings = {
            self._normalize_key(camera_host): {
                "streamId": str(item.get("streamId") or ""),
                "cvrHost": str(item.get("cvrHost") or ""),
                "cvrPort": int(item.get("cvrPort") or DEFAULT_CVR_PORT),
                "username": str(item.get("username") or ""),
                "password": str(item.get("password") or ""),
            }
            for camera_host, item in raw.items()
            if isinstance(item, dict)
        }

    @staticmethod
    def _normalize_key(host: str) -> str:
        return str(host).strip().lower()

    def get(self, host: str) -> dict[str, Any] | None:
        """按摄像头 IP 查映射（含密码，仅供内部解析设备凭据用）；未命中返回 None。"""
        with self._lock:
            mapping = self._mappings.get(self._normalize_key(host))
            return dict(mapping) if mapping is not None else None

    def all(self) -> list[dict[str, Any]]:
        """返回全部映射的对外视图（cameraHost/streamId/cvrHost/cvrPort/username），不含密码。"""
        with self._lock:
            return [
                {
                    "cameraHost": camera_host,
                    "streamId": mapping["streamId"],
                    "cvrHost": mapping["cvrHost"],
                    "cvrPort": mapping["cvrPort"],
                    "username": mapping["username"],
                }
                for camera_host, mapping in self._mappings.items()
            ]

    def import_rows(self, rows: list[Any], cvr: dict[str, Any]) -> dict[str, Any]:
        """批量导入/覆盖（同 cameraHost 覆盖），返回 {"imported": N, "skipped": [...]}。

        每行需含 ``streamId`` 与 ``cameraHost``；``cvr``（{host, port, username, password}）
        对整批生效，port 缺省 8000。校验不通过的行跳过并在 skipped 中给出原因：
        streamId 去掉 ``*`` 与空白后必须非空（导出清单可能用 * 打码）、cameraHost 必须是
        合法 IPv4 地址、cvr.host 必须非空。
        """
        cvr_host = str(cvr.get("host") or "").strip()
        cvr_port = int(cvr.get("port") or DEFAULT_CVR_PORT)
        cvr_username = str(cvr.get("username") or "")
        cvr_password = str(cvr.get("password") or "")
        imported = 0
        skipped: list[dict[str, Any]] = []
        with self._lock:
            for row in rows:
                if not isinstance(row, dict):
                    skipped.append({"row": row, "reason": "row must be an object with streamId/cameraHost"})
                    continue
                reason = self._validate_row(row, cvr_host)
                if reason is not None:
                    skipped.append({"row": row, "reason": reason})
                    continue
                camera_host = self._normalize_key(str(row["cameraHost"]))
                self._mappings[camera_host] = {
                    "streamId": str(row["streamId"]).strip(),
                    "cvrHost": cvr_host,
                    "cvrPort": cvr_port,
                    "username": cvr_username,
                    "password": cvr_password,
                }
                imported += 1
            if imported:
                self._save_locked()
        return {"imported": imported, "skipped": skipped}

    @staticmethod
    def _validate_row(row: dict[str, Any], cvr_host: str) -> str | None:
        """返回该行的跳过原因；可导入时返回 None。"""
        stream_id = str(row.get("streamId") or "")
        if not stream_id.replace("*", "").strip():
            return "streamId 为空（去除 * 与空白后）"
        camera_host = str(row.get("cameraHost") or "").strip()
        if not _is_ipv4(camera_host):
            return f"cameraHost 不是合法 IPv4 地址: {camera_host or '(空)'}"
        if not cvr_host:
            return "cvr.host 为空"
        return None

    def _save_locked(self) -> None:
        # 先写临时文件再 os.replace 原子替换，避免进程中断留下半截 JSON
        directory = os.path.dirname(self._file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        tmp_path = f"{self._file_path}.tmp"
        Path(tmp_path).write_text(
            json.dumps(self._mappings, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(tmp_path, self._file_path)


def _is_ipv4(value: str) -> bool:
    try:
        return isinstance(ip_address(value), IPv4Address)
    except ValueError:
        return False
