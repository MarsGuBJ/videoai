"""Worker 节点心跳与查询契约测试：TestClient 直连，DB 落库在测试中 mock。"""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

import app.services.worker_nodes as worker_nodes_service
from app import state

GPU_BUSY = {
    "index": 0,
    "name": "NVIDIA A10",
    "memoryTotalMb": 23028,
    "memoryUsedMb": 18000,
    "temperatureC": 65,
    "powerW": 145.5,
    "utilizationPct": 80,
}
GPU_IDLE = {
    "index": 1,
    "name": "NVIDIA A10",
    "memoryTotalMb": 23028,
    "memoryUsedMb": 500,
    "temperatureC": 40,
    "powerW": 30.2,
    "utilizationPct": 10,
}

SYSTEM_METRICS = {
    "cpuPercent": 42.5,
    "memoryTotalMb": 128000,
    "memoryUsedMb": 64000,
    "diskTotalGb": 460.0,
    "diskUsedGb": 120.5,
}

HEARTBEAT_PAYLOAD = {
    "hostname": "gpu-worker-1",
    "ip": "192.168.11.194",
    "port": 8090,
    "gpus": [GPU_BUSY, GPU_IDLE],
    "system": SYSTEM_METRICS,
}


def _no_persist(monkeypatch) -> None:
    monkeypatch.setattr(worker_nodes_service, "persist_worker_node", lambda record: None)


def test_list_worker_nodes_empty_store_returns_empty_list(client: TestClient):
    response = client.get("/api/worker-nodes")

    assert response.status_code == 200
    assert response.json() == []


def test_heartbeat_creates_online_node_with_gpu_statuses(client: TestClient, monkeypatch):
    _no_persist(monkeypatch)

    response = client.post("/api/internal/workers/heartbeat", json=HEARTBEAT_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "gpu-worker-1"
    assert body["hostname"] == "gpu-worker-1"
    assert body["ip"] == "192.168.11.194"
    assert body["port"] == 8090
    assert body["status"] == "在线"
    assert body["lastSeenAt"]
    assert body["createdAt"]
    assert body["updatedAt"]
    assert len(body["gpus"]) == 2
    assert body["gpus"][0]["status"] == "繁忙"
    assert body["gpus"][0]["utilizationPct"] == 80
    assert body["gpus"][1]["status"] == "空闲"
    assert body["system"] == SYSTEM_METRICS

    nodes = client.get("/api/worker-nodes").json()
    assert len(nodes) == 1
    assert nodes[0]["hostname"] == "gpu-worker-1"
    assert nodes[0]["status"] == "在线"
    assert nodes[0]["gpus"][0]["status"] == "繁忙"
    assert nodes[0]["gpus"][1]["status"] == "空闲"
    assert nodes[0]["system"]["cpuPercent"] == 42.5


def test_heartbeat_without_system_defaults_to_zero(client: TestClient, monkeypatch):
    """旧版 worker 心跳不带 system 字段，对外返回全零默认值。"""
    _no_persist(monkeypatch)
    payload = {key: value for key, value in HEARTBEAT_PAYLOAD.items() if key != "system"}

    body = client.post("/api/internal/workers/heartbeat", json=payload).json()

    assert body["system"]["cpuPercent"] == 0.0
    assert body["system"]["memoryTotalMb"] == 0


def test_second_heartbeat_updates_same_node(client: TestClient, monkeypatch):
    _no_persist(monkeypatch)

    first = client.post("/api/internal/workers/heartbeat", json=HEARTBEAT_PAYLOAD).json()
    second = client.post(
        "/api/internal/workers/heartbeat",
        json={**HEARTBEAT_PAYLOAD, "gpus": [GPU_IDLE]},
    ).json()

    assert second["id"] == first["id"]
    assert second["createdAt"] == first["createdAt"]
    assert second["lastSeenAt"] >= first["lastSeenAt"]
    assert len(second["gpus"]) == 1

    nodes = client.get("/api/worker-nodes").json()
    assert len(nodes) == 1


def test_stale_node_reported_offline_with_offline_gpus(client: TestClient, monkeypatch):
    _no_persist(monkeypatch)
    now = datetime.now(timezone.utc)
    state.worker_nodes_store["stale-worker"] = {
        "id": "stale-worker",
        "hostname": "stale-worker",
        "ip": "10.0.0.1",
        "port": 8090,
        "gpus": [dict(GPU_BUSY)],
        "last_seen_at": now - timedelta(seconds=120),
        "created_at": now - timedelta(days=1),
        "updated_at": now - timedelta(seconds=120),
    }

    nodes = client.get("/api/worker-nodes").json()

    assert len(nodes) == 1
    assert nodes[0]["status"] == "离线"
    assert nodes[0]["gpus"][0]["status"] == "离线"
