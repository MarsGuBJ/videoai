"""算法管理 API 集成测试：TestClient 全流程（安装/版本/备份/激活/布控绑定）。"""

import io
import zipfile
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.services.algorithms as algo_service
from app.core.config import get_settings

FACE_ZIP_FILES = {
    "face_engine.py": b"py",
    "retinaface_mobilenet0.25.onnx": b"retina",
    "arcface_finetune.onnx": b"arcface",
}


def zip_bytes(files: dict[str, bytes]) -> bytes:
    """把 {路径: 内容} 打成内存 zip 字节串。"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return buffer.getvalue()


@pytest.fixture()
def algo_storage(tmp_path, monkeypatch):
    """把算法安装目录指向 tmp_path，并屏蔽数据库持久化。"""
    monkeypatch.setattr(get_settings(), "storage_algorithm_dir", tmp_path)
    monkeypatch.setattr(algo_service, "persist_algorithm", lambda record: None)
    return tmp_path


def _create_algorithm(client: TestClient, **overrides) -> dict:
    form = {"name": "人脸算法", "code": "face-01", "engineType": "face", "version": "v1.0.0", **overrides}
    files = {"file": ("algo.zip", zip_bytes(FACE_ZIP_FILES), "application/zip")}
    response = client.post("/api/algorithms", data=form, files=files)
    assert response.status_code == 200
    return response.json()


def test_algorithm_engines_list(client: TestClient):
    response = client.get("/api/algorithm-engines")

    assert response.status_code == 200
    engines = {item["engineType"]: item for item in response.json()}
    assert {"face", "head", "helmet", "kpt", "smoke"} <= engines.keys()
    assert engines["face"]["requiredFiles"] == [
        "face_engine.py",
        "retinaface_mobilenet0.25.onnx",
        "arcface_finetune.onnx",
    ]
    assert engines["smoke"]["optionalFiles"] == ["yolov26_1126.onnx"]


def test_create_algorithm_duplicate_code_returns_400(client: TestClient, algo_storage):
    _create_algorithm(client)
    form = {"name": "重复", "code": "face-01", "engineType": "face", "version": "v9.9.9"}
    files = {"file": ("algo.zip", zip_bytes(FACE_ZIP_FILES), "application/zip")}

    response = client.post("/api/algorithms", data=form, files=files)

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_create_algorithm_unknown_engine_returns_400(client: TestClient, algo_storage):
    form = {"name": "未知引擎", "code": "x-01", "engineType": "nope", "version": "v1.0.0"}
    files = {"file": ("algo.zip", zip_bytes({"a.py": b"x"}), "application/zip")}

    response = client.post("/api/algorithms", data=form, files=files)

    assert response.status_code == 400
    assert "Unknown engineType" in response.json()["detail"]


def test_create_algorithm_missing_required_file_returns_400(client: TestClient, algo_storage):
    form = {"name": "缺文件", "code": "face-02", "engineType": "face", "version": "v1.0.0"}
    files = {"file": ("algo.zip", zip_bytes({"face_engine.py": b"py"}), "application/zip")}

    response = client.post("/api/algorithms", data=form, files=files)

    assert response.status_code == 400
    assert "arcface_finetune.onnx" in response.json()["detail"]


def test_algorithm_version_lifecycle_and_backup(client: TestClient, algo_storage):
    created = _create_algorithm(client, versionName="首版", notes="初始版本")
    algorithm_id = created["id"]
    assert created["engineLabel"] == "人脸检测识别"
    assert created["versionCount"] == 1
    assert created["currentVersion"] == "v1.0.0"
    assert created["currentVersionStatus"] == "READY"
    assert created["missingFiles"] == []
    assert (algo_storage / "face-01" / "v1.0.0" / "face_engine.py").is_file()

    listed = client.get("/api/algorithms").json()
    assert [item["id"] for item in listed] == [algorithm_id]

    # 新增版本：生成 .backup 并切换 currentVersion
    new_files = {**FACE_ZIP_FILES, "face_engine.py": b"py-v2"}
    response = client.post(
        f"/api/algorithms/{algorithm_id}/versions",
        data={"version": "v1.1.0", "versionName": "优化版"},
        files={"file": ("algo.zip", zip_bytes(new_files), "application/zip")},
    )
    assert response.status_code == 200
    assert response.json()["version"] == "v1.1.0"
    assert response.json()["active"] is True

    backups = list((algo_storage / "face-01" / ".backup").iterdir())
    assert len(backups) == 1
    assert backups[0].name.startswith("v1.0.0-")
    assert (backups[0] / "face_engine.py").read_bytes() == b"py"
    assert (algo_storage / "face-01" / "v1.1.0" / "face_engine.py").read_bytes() == b"py-v2"

    versions = client.get(f"/api/algorithms/{algorithm_id}/versions").json()
    assert len(versions) == 2
    by_version = {item["version"]: item for item in versions}
    assert by_version["v1.1.0"]["active"] is True
    assert by_version["v1.0.0"]["active"] is False
    assert by_version["v1.0.0"]["fileManifest"]["face_engine.py"] == 2

    # 激活旧版本：再次备份并切回指针
    response = client.post(f"/api/algorithms/{algorithm_id}/versions/{by_version['v1.0.0']['id']}/activate")
    assert response.status_code == 200
    assert response.json()["active"] is True
    backups = list((algo_storage / "face-01" / ".backup").iterdir())
    assert len(backups) == 2
    assert any(item.name.startswith("v1.1.0-") for item in backups)

    detail = client.get("/api/algorithms").json()[0]
    assert detail["currentVersion"] == "v1.0.0"
    assert detail["versionCount"] == 2


def test_update_algorithm_status_and_fields(client: TestClient, algo_storage):
    created = _create_algorithm(client)
    algorithm_id = created["id"]

    response = client.patch(
        f"/api/algorithms/{algorithm_id}",
        json={"name": "人脸算法（改）", "owner": "张三", "status": "DISABLED"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "人脸算法（改）"
    assert payload["owner"] == "张三"
    assert payload["status"] == "DISABLED"
    assert payload["code"] == "face-01"

    bad = client.patch(f"/api/algorithms/{algorithm_id}", json={"status": "BOGUS"})
    assert bad.status_code == 400

    missing = client.patch(f"/api/algorithms/{uuid4()}", json={"name": "x"})
    assert missing.status_code == 404


def test_bind_deployment_task_to_algorithm(client: TestClient, algo_storage):
    created = _create_algorithm(client)

    response = client.post(
        "/api/deployment-tasks",
        json={"name": "绑定算法任务", "cameraIds": [], "algorithmId": created["id"]},
    )

    assert response.status_code == 200
    task = response.json()
    assert task["algorithmId"] == created["id"]
    assert task["algorithmName"] == "人脸算法"
    assert task["engineType"] == "face"


def test_bind_deployment_task_unknown_algorithm_returns_400(client: TestClient, algo_storage):
    response = client.post(
        "/api/deployment-tasks",
        json={"name": "绑定不存在", "cameraIds": [], "algorithmId": str(uuid4())},
    )

    assert response.status_code == 400


def test_bind_deployment_task_missing_files_algorithm_returns_400(client: TestClient, algo_storage):
    form = {"name": "抽烟算法", "code": "smoke-01", "engineType": "smoke", "version": "v1.0.0"}
    files = {"file": ("algo.zip", zip_bytes({"smoke_engine.py": b"py"}), "application/zip")}
    created = client.post("/api/algorithms", data=form, files=files).json()
    assert created["currentVersionStatus"] == "MISSING_FILES"
    assert created["missingFiles"] == ["yolov26_1126.onnx"]

    response = client.post(
        "/api/deployment-tasks",
        json={"name": "绑定缺文件", "cameraIds": [], "algorithmId": created["id"]},
    )

    assert response.status_code == 400
    assert "missing files" in response.json()["detail"]


def test_bind_deployment_task_disabled_algorithm_returns_400(client: TestClient, algo_storage):
    created = _create_algorithm(client)
    client.patch(f"/api/algorithms/{created['id']}", json={"status": "DISABLED"})

    response = client.post(
        "/api/deployment-tasks",
        json={"name": "绑定停用", "cameraIds": [], "algorithmId": created["id"]},
    )

    assert response.status_code == 400
    assert "disabled" in response.json()["detail"]


def test_object_ingest_accepts_event_type_and_deployment_task_id(client: TestClient):
    task_id = str(uuid4())
    payload = {
        "cameraId": str(uuid4()),
        "cameraName": "东门",
        "objects": [{"labelId": 1, "labelName": "person", "score": 0.9, "x1": 0, "y1": 0, "x2": 10, "y2": 10}],
        "videoTime": "2026-01-01T00:00:00Z",
        "eventType": "smoke",
        "deploymentTaskId": task_id,
    }

    response = client.post("/api/events/object-ingest", json=payload)

    assert response.status_code == 200
    event = response.json()
    assert event["eventType"] == "smoke"
    assert event["deploymentTaskId"] == task_id
