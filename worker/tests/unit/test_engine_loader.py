"""引擎加载器单测：mock onnxruntime，构造假引擎目录验证成功路径、缺模型报错与桩注入。"""

import sys
import types
from pathlib import Path
from uuid import uuid4

import pytest
import yaml

from app.engines import loader
from app.schemas import AlgorithmSpec

FAKE_SMOKE_ENGINE = '''
import onnxruntime as ort


class SmokeDetectionEngine:
    def __init__(self):
        self.session = ort.InferenceSession("placeholder.onnx", providers=["CPUExecutionProvider"])

    def inference(self, frame):
        return [[1.0, 2.0, 3.0, 4.0, 0.9, 0]]

    def build_result(self, raw):
        return {"eventType": "SD_抽烟检测"}
'''

# 与真实 helmet_engine 一样引用 demo 中缺失的 YOLO11HelmetConfig，验证 shim 注入
FAKE_HELMET_ENGINE = '''
import onnxruntime as ort
from src.config.model.YOLO11HelmetConfig import YOLO11InferConfig


class HelmetDetectionEngine:
    def __init__(self):
        self.model_path = YOLO11InferConfig.getCurrentHelmetDetectionModelPath()
        self.session = ort.InferenceSession(self.model_path, providers=["CPUExecutionProvider"])

    def inference(self, frame):
        return []

    def build_result(self, raw):
        return {"eventType": "SD_安全帽检测"}
'''

# 与真实 face_engine 一样 import elasticsearch/minio 与 src.base 下的 ES/MinIO 模块，验证桩注入
FAKE_FACE_ENGINE = '''
import onnxruntime as ort
import elasticsearch  # noqa: F401  # 环境中未安装，依赖加载器桩模块
import minio  # noqa: F401
from src.base.ESHandler.FaceFeatureVectorHandler import FeatureVectorHandler
from src.base.minio.MinioPySDK import minioClient


class FaceDetectionEngine:
    def __init__(self):
        self.det_sess = ort.InferenceSession("det.onnx", providers=["CPUExecutionProvider"])
        self.rec_sess = ort.InferenceSession("rec.onnx", providers=["CPUExecutionProvider"])

    def search(self):
        return FeatureVectorHandler.retrievalByFeature(query_vector=None, top_n=1)

    def upload(self):
        return minioClient.uploadImageByStream(bucketName="b", objectName="o", byteStream=b"")

    def inference(self, frame):
        return {"bboxes": [], "identities": []}

    def build_result(self, raw):
        return {"eventType": "SD_身份验证"}
'''


class _FakeInferenceSession:
    def __init__(self, path, providers=None):
        self.path = path
        self.providers = providers


@pytest.fixture(autouse=True)
def fake_onnxruntime(monkeypatch):
    fake_ort = types.ModuleType("onnxruntime")
    fake_ort.InferenceSession = _FakeInferenceSession
    monkeypatch.setitem(sys.modules, "onnxruntime", fake_ort)


@pytest.fixture(autouse=True)
def clean_loader_state(tmp_path):
    yield
    # 清理加载器注入的 src.* / 桩模块与 sys.path 中的临时引擎目录，避免用例间串扰
    for name in [n for n in sys.modules if n == "src" or n.startswith("src.")]:
        sys.modules.pop(name, None)
    stubbed = ("elasticsearch", "elasticsearch_dsl", "minio", "minio.datatypes", "minio.deleteobjects", "minio.helpers")
    for name in stubbed:
        sys.modules.pop(name, None)
    loader._engine_cache.clear()
    sys.path[:] = [p for p in sys.path if not str(p).startswith(str(tmp_path))]


def make_install_dir(root: Path, kind: str, engine_source: str, models: list[str]) -> Path:
    install = root / "algo" / "v1"
    install.mkdir(parents=True)
    (install / loader.ENGINE_REGISTRY[kind].module_file).write_text(engine_source, encoding="utf-8")
    for name in models:
        (install / name).write_bytes(b"")
    return install


def make_spec(kind: str, install: Path) -> AlgorithmSpec:
    return AlgorithmSpec(algorithmId=uuid4(), engineType=kind, version="1.0.0", installPath=str(install))


def make_src_packages(install: Path, *packages: str) -> None:
    for package in packages:
        package_dir = install / Path(package.replace(".", "/"))
        package_dir.mkdir(parents=True, exist_ok=True)
        package_dir.joinpath("__init__.py").write_text("", encoding="utf-8")


def test_load_engine_success_and_writes_inference_yaml(tmp_path):
    install = make_install_dir(tmp_path, "smoke", FAKE_SMOKE_ENGINE, ["yolov26_1126.onnx"])

    engine = loader.load_engine(make_spec("smoke", install))

    assert isinstance(engine.session, _FakeInferenceSession)
    # 配置类按 inference.model.smoke.yolo26.model_path 读取（supported_model[1] == yolo26）
    config = yaml.safe_load((install / "resource" / "inference.yaml").read_text(encoding="utf-8"))
    smoke = config["inference"]["model"]["smoke"]
    assert smoke["supported_model"][1] == "yolo26"
    assert smoke["yolo26"]["model_path"] == str((install / "yolov26_1126.onnx").resolve())


def test_load_engine_missing_model_files_raises(tmp_path):
    fake_kpt_engine = FAKE_SMOKE_ENGINE.replace("SmokeDetectionEngine", "KptDetectionEngine")
    install = make_install_dir(tmp_path, "kpt", fake_kpt_engine, ["yolov8.onnx"])

    with pytest.raises(loader.EngineLoadError, match="dark_hrnet.onnx"):
        loader.load_engine(make_spec("kpt", install))


def test_load_engine_unknown_type_raises(tmp_path):
    spec = AlgorithmSpec(algorithmId=uuid4(), engineType="unknown", version="1.0.0", installPath=str(tmp_path))

    with pytest.raises(loader.EngineLoadError, match="未知的引擎类型"):
        loader.load_engine(spec)


def test_helmet_config_shim_injected(tmp_path):
    install = make_install_dir(tmp_path, "helmet", FAKE_HELMET_ENGINE, ["helmet_v6.onnx"])
    make_src_packages(install, "src", "src.config", "src.config.model")  # 故意不提供 YOLO11HelmetConfig.py

    engine = loader.load_engine(make_spec("helmet", install))

    assert engine.model_path == str((install / "helmet_v6.onnx").resolve())
    shim = sys.modules["src.config.model.YOLO11HelmetConfig"]
    assert shim.YOLO11InferConfig.getCurrentHelmetDetectionModelPath() == engine.model_path


def test_face_engine_stub_modules_injected(tmp_path):
    install = make_install_dir(
        tmp_path,
        "face",
        FAKE_FACE_ENGINE,
        ["retinaface_mobilenet0.25.onnx", "arcface_finetune.onnx"],
    )
    make_src_packages(install, "src", "src.base", "src.base.ESHandler", "src.base.minio")

    engine = loader.load_engine(make_spec("face", install))

    # ES 检索桩：恒返回空结果，引擎异步识别落入“陌生人”分支
    assert engine.search().scoreEmpty is True
    assert engine.search().searchResults == []
    # MinIO 桩：上传为 no-op
    assert engine.upload() is None
    assert isinstance(sys.modules["elasticsearch"], types.ModuleType)
    assert isinstance(sys.modules["minio"], types.ModuleType)


def test_acquire_engine_caches_per_camera_and_release(tmp_path):
    install = make_install_dir(tmp_path, "smoke", FAKE_SMOKE_ENGINE, ["yolov26_1126.onnx"])
    spec = make_spec("smoke", install)
    camera_key = str(uuid4())

    first = loader.acquire_engine(camera_key, spec)
    second = loader.acquire_engine(camera_key, spec)
    assert first is second

    loader.release_engine(camera_key)
    third = loader.acquire_engine(camera_key, spec)
    assert third is not first
    loader.release_engine(camera_key)


def test_raw_to_objects_kpt_uses_bbox():
    raw = {"keypoint": [[[[1.0, 2.0, 0.9]]], [[0.9]]], "bbox": [[10.0, 20.0, 30.0, 40.0]]}

    objects = loader.raw_to_objects("kpt", raw)

    assert objects == [
        {"labelId": 0, "labelName": "person_kpt", "score": 1.0, "x1": 10.0, "y1": 20.0, "x2": 30.0, "y2": 40.0}
    ]


def test_raw_to_objects_smoke_rows():
    objects = loader.raw_to_objects("smoke", [[1.0, 2.0, 3.0, 4.0, 0.9, 1]])

    assert objects == [{"labelId": 1, "labelName": "smoke", "score": 0.9, "x1": 1.0, "y1": 2.0, "x2": 3.0, "y2": 4.0}]
    assert loader.raw_to_objects("smoke", []) == []
