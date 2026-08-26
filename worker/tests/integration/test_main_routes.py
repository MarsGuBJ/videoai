"""main.py 路由测试：TestClient 直连，stream manager 在使用处（app.main 命名空间）mock。"""

from uuid import uuid4

from fastapi.testclient import TestClient

import app.main as worker_main


def test_health_returns_ok():
    client = TestClient(worker_main.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_start_stream_delegates_to_stream_manager(monkeypatch):
    started = []

    class FakeStreamManager:
        def start(self, request):
            started.append(request)

        def status(self):
            return {"cam-1": "running"}

    # mock 边界：路由内调用的进程级单例工厂，在使用处替换
    monkeypatch.setattr(worker_main, "stream_manager", lambda: FakeStreamManager())
    client = TestClient(worker_main.app)
    payload = {
        "cameraId": str(uuid4()),
        "cameraName": "北门",
        "streamUrl": "rtsp://camera/live",
    }

    start_response = client.post("/v1/streams/start", json=payload)
    list_response = client.get("/v1/streams")

    assert start_response.status_code == 200
    assert start_response.json() == {"status": "started"}
    assert len(started) == 1
    assert str(started[0].cameraId) == payload["cameraId"]
    assert list_response.status_code == 200
    assert list_response.json() == {"streams": {"cam-1": "running"}}
