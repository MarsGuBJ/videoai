"""monitor 单元测试：GPU 采集（假 pynvml）、心跳 payload 与异常回退。"""

import types

import pytest
import requests

from app import monitor


@pytest.fixture(autouse=True)
def _reset_nvml_state(monkeypatch):
    """每个用例重置 NVML 惰性初始化状态，避免用例间串扰。"""
    monkeypatch.setattr(monitor, "_nvml_initialized", False)
    monkeypatch.setattr(monitor, "_nvml_failed", False)


def make_fake_pynvml() -> types.SimpleNamespace:
    """构造一块假 GPU 的 pynvml 桩：name 返回 bytes，功率单位 mW。"""
    fake = types.SimpleNamespace(NVML_TEMPERATURE_GPU=0)
    fake.nvmlInit = lambda: None
    fake.nvmlDeviceGetCount = lambda: 1
    fake.nvmlDeviceGetHandleByIndex = lambda index: f"handle-{index}"
    fake.nvmlDeviceGetName = lambda handle: b"NVIDIA A10"
    fake.nvmlDeviceGetMemoryInfo = lambda handle: types.SimpleNamespace(
        total=23028 * 1024 * 1024,
        used=4096 * 1024 * 1024,
    )
    fake.nvmlDeviceGetTemperature = lambda handle, sensor: 65
    fake.nvmlDeviceGetPowerUsage = lambda handle: 145500  # mW
    fake.nvmlDeviceGetUtilizationRates = lambda handle: types.SimpleNamespace(gpu=80)
    return fake


def test_collect_gpu_metrics_parses_fake_pynvml(monkeypatch):
    monkeypatch.setattr(monitor, "pynvml", make_fake_pynvml())

    metrics = monitor.collect_gpu_metrics()

    assert metrics == [
        {
            "index": 0,
            "name": "NVIDIA A10",
            "memoryTotalMb": 23028,
            "memoryUsedMb": 4096,
            "temperatureC": 65,
            "powerW": 145.5,
            "utilizationPct": 80,
        }
    ]


def test_collect_gpu_metrics_returns_empty_without_pynvml(monkeypatch):
    monkeypatch.setattr(monitor, "pynvml", None)

    assert monitor.collect_gpu_metrics() == []


def test_collect_gpu_metrics_returns_empty_when_nvml_init_raises(monkeypatch):
    fake = make_fake_pynvml()

    def _raise():
        raise RuntimeError("NVMLError: no GPU")

    fake.nvmlInit = _raise
    monkeypatch.setattr(monitor, "pynvml", fake)

    assert monitor.collect_gpu_metrics() == []


def test_heartbeat_once_posts_expected_payload(monkeypatch):
    monkeypatch.setattr(monitor, "pynvml", make_fake_pynvml())
    monkeypatch.setattr(monitor, "collect_node_info", lambda: ("gpu-worker-1", "192.168.11.194"))
    captured = {}

    def _fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return types.SimpleNamespace(raise_for_status=lambda: None)

    monkeypatch.setattr(monitor.requests, "post", _fake_post)

    assert monitor.heartbeat_once() is True
    assert captured["url"] == "http://localhost:8081/api/internal/workers/heartbeat"
    assert captured["timeout"] == 5
    assert captured["json"]["hostname"] == "gpu-worker-1"
    assert captured["json"]["ip"] == "192.168.11.194"
    assert captured["json"]["port"] == 8090
    assert len(captured["json"]["gpus"]) == 1
    assert captured["json"]["gpus"][0]["utilizationPct"] == 80


def test_heartbeat_once_prefers_configured_node_identity(monkeypatch):
    """配置了固定节点名/IP 时，心跳覆盖容器默认 hostname 与自动探测 IP。"""
    monkeypatch.setattr(monitor, "collect_gpu_metrics", lambda: [])
    monkeypatch.setattr(monitor, "collect_system_metrics", lambda: {})
    monkeypatch.setattr(monitor, "collect_node_info", lambda: ("container-id", "10.0.0.1"))
    monkeypatch.setattr(
        monitor,
        "settings",
        lambda: types.SimpleNamespace(
            backend_internal_url="http://localhost:8081",
            worker_port=8090,
            worker_node_name="videoai-worker",
            worker_node_ip="192.168.11.194",
        ),
    )
    captured = {}

    def _fake_post(url, json, timeout):
        captured["json"] = json
        return types.SimpleNamespace(raise_for_status=lambda: None)

    monkeypatch.setattr(monitor.requests, "post", _fake_post)

    assert monitor.heartbeat_once() is True
    assert captured["json"]["hostname"] == "videoai-worker"
    assert captured["json"]["ip"] == "192.168.11.194"


def test_heartbeat_once_returns_false_on_request_exception(monkeypatch):
    monkeypatch.setattr(monitor, "collect_gpu_metrics", lambda: [])

    def _raise(url, json, timeout):
        raise requests.ConnectionError("connection refused")

    monkeypatch.setattr(monitor.requests, "post", _raise)

    assert monitor.heartbeat_once() is False
