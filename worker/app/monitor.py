"""Worker 节点资源监控：GPU 指标采集（pynvml 可选）、系统指标采集（psutil 可选）与心跳上报。

pynvml / psutil 均为可选运行时依赖：无 GPU / 无依赖环境下采集返回空列表或空字典，
心跳仍然照常上报（gpus=[] / system={}），监控绝不阻断推理主流程。
"""

import logging
import os
import socket
import threading
from typing import Any

import requests

from .config import settings

logger = logging.getLogger(__name__)

try:
    import pynvml  # type: ignore[import-not-found]
except ImportError:  # 无 pynvml 环境仍可运行 worker
    pynvml = None

try:
    import psutil  # type: ignore[import-not-found]
except ImportError:  # 无 psutil 环境仍可运行 worker
    psutil = None

_nvml_initialized = False
_nvml_failed = False

HEARTBEAT_TIMEOUT_SECONDS = 5

# 容器内 / 是 overlay 文件系统，不能代表宿主机磁盘；
# compose 把宿主机根目录只读挂载到 /host，优先采集它
DISK_PATH = "/host" if os.path.isdir("/host") else "/"


def collect_gpu_metrics() -> list[dict[str, Any]]:
    """采集本机全部 GPU 指标；任何异常（无 pynvml / 无 GPU / NVMLError）均返回 []。"""
    global _nvml_initialized, _nvml_failed
    if pynvml is None:
        return []
    try:
        if not _nvml_initialized:
            pynvml.nvmlInit()
            _nvml_initialized = True
        metrics: list[dict[str, Any]] = []
        for index in range(pynvml.nvmlDeviceGetCount()):
            handle = pynvml.nvmlDeviceGetHandleByIndex(index)
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode("utf-8", errors="replace")
            memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
            metrics.append(
                {
                    "index": index,
                    "name": str(name),
                    "memoryTotalMb": int(memory.total // (1024 * 1024)),
                    "memoryUsedMb": int(memory.used // (1024 * 1024)),
                    "temperatureC": int(pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)),
                    "powerW": round(pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0, 1),
                    "utilizationPct": int(pynvml.nvmlDeviceGetUtilizationRates(handle).gpu),
                }
            )
        return metrics
    except Exception as exc:  # noqa: BLE001  # 监控采集绝不影响推理主流程
        if not _nvml_failed:  # 失败只记一次日志，避免心跳周期刷屏
            logger.warning("gpu metrics collect failed: %s", exc)
            _nvml_failed = True
        return []


def collect_system_metrics() -> dict[str, Any]:
    """采集宿主机 CPU/内存/磁盘指标；任何异常均返回 {}。

    容器共享宿主机内核，psutil 读取的 /proc/stat 与 /proc/meminfo 为宿主机口径；
    磁盘走 DISK_PATH（compose 挂载的宿主机根目录 /host，未挂载时回退 /）。
    cpu_percent 非阻塞采样（相对上次调用），心跳周期调用下首次为 0 属正常。
    """
    if psutil is None:
        return {}
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(DISK_PATH)
        return {
            "cpuPercent": round(float(psutil.cpu_percent(interval=None)), 1),
            "memoryTotalMb": int(memory.total // (1024 * 1024)),
            "memoryUsedMb": int(memory.used // (1024 * 1024)),
            "diskTotalGb": round(disk.total / (1024**3), 1),
            "diskUsedGb": round(disk.used / (1024**3), 1),
        }
    except Exception as exc:  # noqa: BLE001  # 监控采集绝不影响推理主流程
        logger.warning("system metrics collect failed: %s", exc)
        return {}


def collect_node_info() -> tuple[str, str]:
    """返回 (hostname, 本机内网 IP)；IP 逐级回退，最终 127.0.0.1。"""
    hostname = socket.gethostname()
    try:
        # UDP connect 不实际发包，仅让内核选出对外网卡地址
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return hostname, str(sock.getsockname()[0])
    except OSError:
        pass
    try:
        return hostname, socket.gethostbyname(hostname)
    except OSError:
        return hostname, "127.0.0.1"


def heartbeat_once() -> bool:
    """向 backend-lite 上报一次心跳；网络异常记日志并返回 False。"""
    hostname, ip = collect_node_info()
    # 配置了固定节点标识/上报 IP 时优先使用，避免容器重建后 hostname 变化产生重复节点
    node_settings = settings()
    hostname = node_settings.worker_node_name or hostname
    ip = node_settings.worker_node_ip or ip
    payload = {
        "hostname": hostname,
        "ip": ip,
        "port": node_settings.worker_port,
        "gpus": collect_gpu_metrics(),
        "system": collect_system_metrics(),
    }
    url = f"{node_settings.backend_internal_url}/api/internal/workers/heartbeat"
    try:
        response = requests.post(url, json=payload, timeout=HEARTBEAT_TIMEOUT_SECONDS)
        response.raise_for_status()
        return True
    except requests.RequestException as exc:
        logger.warning("worker heartbeat failed: %s", exc)
        return False


def heartbeat_loop(stop_event: threading.Event) -> None:
    """周期心跳循环：上报一次后等待 monitor_interval_seconds，直到 stop_event 置位。"""
    while not stop_event.is_set():
        heartbeat_once()
        stop_event.wait(settings().monitor_interval_seconds)
