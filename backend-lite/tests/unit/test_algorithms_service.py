"""算法安装服务单测：zip 校验、可选文件缺失、版本备份目录。"""

import io
import zipfile
from uuid import uuid4

import pytest
from fastapi import HTTPException, UploadFile

from app import state
from app.core.config import get_settings
from app.services import algorithms as algo_service


def make_upload(files: dict[str, bytes]) -> UploadFile:
    """把 {路径: 内容} 打成内存 zip 并包装为 UploadFile。"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    buffer.seek(0)
    return UploadFile(file=buffer, filename="algo.zip")


@pytest.fixture()
def algo_storage(tmp_path, monkeypatch):
    """把算法安装目录指向 tmp_path，并屏蔽数据库持久化。"""
    monkeypatch.setattr(get_settings(), "storage_algorithm_dir", tmp_path)
    monkeypatch.setattr(algo_service, "persist_algorithm", lambda record: None)
    state.algorithms_store.clear()
    yield tmp_path
    state.algorithms_store.clear()


def test_install_rejects_invalid_zip(algo_storage):
    bad = UploadFile(file=io.BytesIO(b"definitely not a zip"), filename="bad.zip")

    with pytest.raises(HTTPException) as exc_info:
        algo_service.install_algorithm_zip(
            algorithm_id=uuid4(),
            code="smoke-01",
            engine_type="smoke",
            version="v1.0.0",
            version_name=None,
            notes=None,
            upload=bad,
        )

    assert exc_info.value.status_code == 400
    assert "not a valid zip" in exc_info.value.detail


def test_install_rejects_path_traversal(algo_storage):
    upload = make_upload({"smoke_engine.py": b"py", "../evil.py": b"evil"})

    with pytest.raises(HTTPException) as exc_info:
        algo_service.install_algorithm_zip(
            algorithm_id=uuid4(),
            code="smoke-01",
            engine_type="smoke",
            version="v1.0.0",
            version_name=None,
            notes=None,
            upload=upload,
        )

    assert exc_info.value.status_code == 400
    assert "illegal path" in exc_info.value.detail


def test_install_missing_required_files_returns_400_with_missing_list(algo_storage):
    upload = make_upload({"face_engine.py": b"py"})

    with pytest.raises(HTTPException) as exc_info:
        algo_service.install_algorithm_zip(
            algorithm_id=uuid4(),
            code="face-01",
            engine_type="face",
            version="v1.0.0",
            version_name=None,
            notes=None,
            upload=upload,
        )

    assert exc_info.value.status_code == 400
    assert "retinaface_mobilenet0.25.onnx" in exc_info.value.detail
    assert "arcface_finetune.onnx" in exc_info.value.detail


def test_smoke_missing_optional_onnx_installs_as_missing_files(algo_storage):
    record = algo_service.create_algorithm(
        name="抽烟识别",
        code="smoke-01",
        engine_type="smoke",
        version="v1.0.0",
        scene=None,
        owner=None,
        description=None,
        version_name=None,
        notes=None,
        upload=make_upload({"smoke_engine.py": b"py"}),
    )

    current = algo_service.current_version_of(record)
    assert current is not None
    assert current.status == "MISSING_FILES"
    assert current.missingFiles == ["yolov26_1126.onnx"]
    install_dir = algo_storage / "smoke-01" / "v1.0.0"
    assert (install_dir / "smoke_engine.py").is_file()
    assert current.fileManifest == {"smoke_engine.py": 2}


def test_install_strips_wrapper_and_preserves_structure(algo_storage):
    record = algo_service.create_algorithm(
        name="人头检测",
        code="head-01",
        engine_type="head",
        version="v1.0.0",
        scene=None,
        owner=None,
        description=None,
        version_name=None,
        notes=None,
        upload=make_upload(
            {
                "pkg/head_engine.py": b"py",
                "pkg/models.onnx": b"onnx",
                "pkg/src/service/HeadService.py": b"svc",
            }
        ),
    )

    install_dir = algo_storage / "head-01" / "v1.0.0"
    # 单层包裹目录被剥离，引擎与模型落在根级
    assert (install_dir / "head_engine.py").is_file()
    assert (install_dir / "models.onnx").is_file()
    # src/ 包目录结构原样保留（worker 动态加载依赖它）
    assert (install_dir / "src" / "service" / "HeadService.py").is_file()
    assert algo_service.current_version_of(record).status == "READY"


def test_install_required_file_nested_in_subdirectory_returns_400(algo_storage):
    upload = make_upload({"utils/head_engine.py": b"py", "models.onnx": b"onnx"})

    with pytest.raises(HTTPException) as exc_info:
        algo_service.install_algorithm_zip(
            algorithm_id=uuid4(),
            code="head-02",
            engine_type="head",
            version="v1.0.0",
            version_name=None,
            notes=None,
            upload=upload,
        )

    assert exc_info.value.status_code == 400
    assert "head_engine.py" in exc_info.value.detail


def test_add_version_creates_backup_of_current_version(algo_storage):
    record = algo_service.create_algorithm(
        name="抽烟识别",
        code="smoke-02",
        engine_type="smoke",
        version="v1.0.0",
        scene=None,
        owner=None,
        description=None,
        version_name=None,
        notes=None,
        upload=make_upload({"smoke_engine.py": b"old", "yolov26_1126.onnx": b"v1"}),
    )

    algo_service.add_version(
        record,
        version="v2.0.0",
        version_name=None,
        notes=None,
        upload=make_upload({"smoke_engine.py": b"new", "yolov26_1126.onnx": b"v2"}),
    )

    backup_root = algo_storage / "smoke-02" / ".backup"
    backups = list(backup_root.iterdir())
    assert len(backups) == 1
    assert backups[0].name.startswith("v1.0.0-")
    assert (backups[0] / "smoke_engine.py").read_bytes() == b"old"
    assert record.currentVersion == "v2.0.0"
    assert (algo_storage / "smoke-02" / "v2.0.0" / "smoke_engine.py").read_bytes() == b"new"


def test_activate_version_creates_backup_and_switches_pointer(algo_storage):
    record = algo_service.create_algorithm(
        name="抽烟识别",
        code="smoke-03",
        engine_type="smoke",
        version="v1.0.0",
        scene=None,
        owner=None,
        description=None,
        version_name=None,
        notes=None,
        upload=make_upload({"smoke_engine.py": b"v1"}),
    )
    added = algo_service.add_version(
        record,
        version="v2.0.0",
        version_name=None,
        notes=None,
        upload=make_upload({"smoke_engine.py": b"v2"}),
    )
    v1_id = next(item.id for item in record.versions.values() if item.version == "v1.0.0")
    backups_before = len(list((algo_storage / "smoke-03" / ".backup").iterdir()))

    target = algo_service.activate_version(record, v1_id)

    assert target.version == "v1.0.0"
    assert record.currentVersion == "v1.0.0"
    backups_after = list((algo_storage / "smoke-03" / ".backup").iterdir())
    assert len(backups_after) == backups_before + 1
    assert any(item.name.startswith("v2.0.0-") for item in backups_after)
    # 重复激活同一版本不再备份
    algo_service.activate_version(record, v1_id)
    assert len(list((algo_storage / "smoke-03" / ".backup").iterdir())) == len(backups_after)
    assert added.id != v1_id
