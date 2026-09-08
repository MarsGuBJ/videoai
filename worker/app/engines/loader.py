"""算法引擎动态加载器。

backend-lite 把用户上传的算法引擎 zip 解压安装到共享目录
``<algorithms_dir>/<code>/<version>/``（引擎 py + onnx 平铺，zip 内需自带引擎
依赖的 ``src`` 包），worker 通过本模块按 ``AlgorithmSpec`` 动态加载并实例化引擎。

关键机制（对照 demo 源码）：

- 引擎配置类（``src/config/InferenceConfig.py`` 读 ``../../resource/inference.yaml``、
  ``src/config/model/*.py`` 读 ``../../../resource/inference.yaml``）都相对**自身文件**
  定位 yaml，与进程 cwd 无关，因此 chdir 无效。本加载器在引擎目录写
  ``resource/inference.yaml``，把所需 onnx 的绝对路径按 ``inference.model.<任务>.<键>``
  结构写好——这是对引擎零侵入且唯一可靠的定位方式。
- demo 缺失 ``src/config/model/YOLO11HelmetConfig.py``（helmet 引擎引用），加载
  helmet 引擎时若真实模块导入失败，则在 ``sys.modules`` 注入同接口 shim，
  ``model_path`` 指向安装目录的 ``helmet_v6.onnx``。
- face 引擎 import 的 ``src.base.ESHandler.FaceFeatureVectorHandler`` /
  ``src.base.minio.MinioPySDK`` 在模块 import 时就会连接 ES/MinIO。本项目人脸比对
  走 Triton + ``/api/internal/match``，不用引擎内识别链路，因此预注入桩模块：
  ``retrievalByFeature`` 恒返回空结果（引擎异步识别流程落入“陌生人”分支并自行
  catch），``minioClient.uploadImageByStream`` 为 no-op。
"""

import importlib.util
import logging
import sys
import threading
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ..config import settings
from ..schemas import AlgorithmSpec

logger = logging.getLogger(__name__)


class EngineLoadError(RuntimeError):
    """算法引擎加载失败（未知类型 / 缺文件 / 导入或初始化失败）。"""


@dataclass(frozen=True)
class EngineEntry:
    """一种引擎的静态描述：模块文件、引擎类、所需 onnx 文件、默认事件类型。"""

    module_file: str
    class_name: str
    models: tuple[str, ...]
    event_type: str
    kind: str  # 结果转换器种类，与规范化后的 engineType 一致


# engineType（小写）→ 引擎描述。onnx 文件名要求安装 zip 保持 demo 中的命名。
ENGINE_REGISTRY: dict[str, EngineEntry] = {
    "face": EngineEntry(
        "face_engine.py",
        "FaceDetectionEngine",
        ("retinaface_mobilenet0.25.onnx", "arcface_finetune.onnx"),
        "SD_身份验证",
        "face",
    ),
    "head": EngineEntry("head_engine.py", "HeadDetectionEngine", ("models.onnx",), "SD_人头检测", "head"),
    "helmet": EngineEntry("helmet_engine.py", "HelmetDetectionEngine", ("helmet_v6.onnx",), "SD_安全帽检测", "helmet"),
    "kpt": EngineEntry(
        "kpt_engine.py",
        "KptDetectionEngine",
        ("yolov8.onnx", "dark_hrnet.onnx"),
        "SD_人体关键点",
        "kpt",
    ),
    "smoke": EngineEntry("smoke_engine.py", "SmokeDetectionEngine", ("yolov26_1126.onnx",), "SD_抽烟检测", "smoke"),
}

# 常见的 engineType 别名归一化
_ENGINE_TYPE_ALIASES = {
    "face_detection": "face",
    "head_count": "head",
    "headcount": "head",
    "helmet_detection": "helmet",
    "keypoint": "kpt",
    "person_kpt": "kpt",
    "smoke_detection": "smoke",
}


def registry_entry(engine_type: str) -> EngineEntry:
    """按 engineType（大小写不敏感，支持少量别名）查引擎描述，未知类型抛 EngineLoadError。"""
    normalized = _ENGINE_TYPE_ALIASES.get(engine_type.strip().lower(), engine_type.strip().lower())
    entry = ENGINE_REGISTRY.get(normalized)
    if entry is None:
        raise EngineLoadError(f"未知的引擎类型: {engine_type}（支持: {sorted(ENGINE_REGISTRY)}）")
    return entry


def load_engine(spec: AlgorithmSpec, base_dir: str | None = None) -> Any:
    """按 AlgorithmSpec 动态加载并实例化引擎，失败抛 EngineLoadError。"""
    entry = registry_entry(spec.engineType)
    install_dir = _resolve_install_dir(spec, base_dir)
    module_path = install_dir / entry.module_file
    if not module_path.is_file():
        raise EngineLoadError(f"引擎文件不存在: {module_path}")
    missing = [name for name in entry.models if not (install_dir / name).is_file()]
    if missing:
        raise EngineLoadError(f"引擎 {spec.engineType} 缺少模型文件: {missing}（目录 {install_dir}）")

    _write_inference_yaml(entry, install_dir)
    _prepare_imports(entry, install_dir)
    module = _import_engine_module(entry, module_path)
    engine_cls = getattr(module, entry.class_name, None)
    if engine_cls is None:
        raise EngineLoadError(f"引擎模块 {module_path} 中找不到类 {entry.class_name}")
    try:
        return engine_cls()
    except EngineLoadError:
        raise
    except Exception as exc:
        raise EngineLoadError(f"引擎 {entry.class_name} 初始化失败: {exc}") from exc


def acquire_engine(camera_key: str, spec: AlgorithmSpec, base_dir: str | None = None) -> Any:
    """按 cameraId 取缓存引擎；规格变化或首次调用时重新加载。"""
    with _cache_lock:
        cached = _engine_cache.get(camera_key)
        if cached is not None:
            cached_spec, engine = cached
            if _same_spec(cached_spec, spec):
                return engine
            _shutdown_engine(engine)
            _engine_cache.pop(camera_key, None)
    # 加载较慢且可能失败，放在锁外，避免阻塞其它相机的取引擎操作
    engine = load_engine(spec, base_dir)
    with _cache_lock:
        _engine_cache[camera_key] = (spec, engine)
    return engine


def release_engine(camera_key: str) -> None:
    """流停止时释放该相机的缓存引擎（face 引擎内部线程池一并 shutdown）。"""
    with _cache_lock:
        cached = _engine_cache.pop(camera_key, None)
    if cached is not None:
        _shutdown_engine(cached[1])


def raw_to_objects(engine_type: str, raw: Any) -> list[dict[str, Any]]:
    """把引擎 inference 原始输出转成 ObjectInfo 字典列表（labelId/labelName/score/x1..y2）。"""
    kind = registry_entry(engine_type).kind
    if raw is None:
        return []
    if kind == "face":
        # {"bboxes": Nx5 (x1,y1,x2,y2,conf), "identities": [...]} —— 识别身份不走引擎，统一标 face
        bboxes = raw.get("bboxes") if isinstance(raw, dict) else None
        if bboxes is None or len(bboxes) == 0:
            return []
        return [_bbox_object(row[:5], label_id=0, label_name="face") for row in bboxes]
    if kind == "kpt":
        # {"keypoint": [...], "bbox": [[x1,y1,x2,y2], ...]} —— 只取 bbox，labelName=person_kpt
        bboxes = raw.get("bbox") if isinstance(raw, dict) else None
        if bboxes is None or len(bboxes) == 0:
            return []
        return [_bbox_object((*row[:4], 1.0), label_id=0, label_name="person_kpt") for row in bboxes]
    # head / helmet / smoke：行结构 [x1, y1, x2, y2, conf, cls]
    if len(raw) == 0:
        return []
    return [_bbox_object(row[:5], label_id=int(row[5]), label_name=kind) for row in raw]


def _bbox_object(values: Any, label_id: int, label_name: str) -> dict[str, Any]:
    x1, y1, x2, y2, score = (float(v) for v in values)
    return {"labelId": label_id, "labelName": label_name, "score": score, "x1": x1, "y1": y1, "x2": x2, "y2": y2}


def _resolve_install_dir(spec: AlgorithmSpec, base_dir: str | None) -> Path:
    install_dir = Path(spec.installPath)
    if not install_dir.is_absolute():
        install_dir = Path(base_dir or settings().algorithms_dir) / install_dir
    return install_dir


def _same_spec(a: AlgorithmSpec, b: AlgorithmSpec) -> bool:
    return (
        a.algorithmId == b.algorithmId
        and a.engineType == b.engineType
        and a.version == b.version
        and a.installPath == b.installPath
    )


def _shutdown_engine(engine: Any) -> None:
    executor = getattr(engine, "executor", None)
    if executor is not None and hasattr(executor, "shutdown"):
        try:
            executor.shutdown(wait=False)
        except Exception:  # noqa: BLE001  # 释放阶段不抛错
            logger.warning("engine executor shutdown failed", exc_info=True)


def _import_engine_module(entry: EngineEntry, module_path: Path) -> types.ModuleType:
    module_name = f"videoai_algorithm_{entry.kind}_{abs(hash(str(module_path)))}"
    module_spec = importlib.util.spec_from_file_location(module_name, module_path)
    if module_spec is None or module_spec.loader is None:
        raise EngineLoadError(f"无法为引擎文件创建模块 spec: {module_path}")
    module = importlib.util.module_from_spec(module_spec)
    try:
        module_spec.loader.exec_module(module)
    except Exception as exc:
        raise EngineLoadError(f"引擎模块 {module_path} 导入失败: {exc}") from exc
    return module


def _prepare_imports(entry: EngineEntry, install_dir: Path) -> None:
    """让引擎的 ``import src...`` 解析到自身安装目录，并按需注入 shim/桩模块。"""
    install_str = str(install_dir)
    if install_str not in sys.path:
        sys.path.insert(0, install_str)
    _evict_foreign_src_modules(install_dir)
    if entry.kind == "face":
        _install_face_stubs()
    if entry.kind == "helmet":
        _ensure_helmet_config_shim(install_dir, entry)


def _evict_foreign_src_modules(install_dir: Path) -> None:
    """引擎 zip 自带 ``src`` 包；若已缓存的 src 模块来自其它安装目录则清除。

    注意：Python 包全局命名空间决定了同一时刻 ``src`` 只能解析到一个安装目录，
    多版本引擎并行时后加载者生效（引擎实例已持有各自模块引用，互不影响运行）。
    """
    cached = sys.modules.get("src")
    if cached is None:
        return
    cached_file = getattr(cached, "__file__", None)
    try:
        if cached_file and Path(cached_file).resolve().is_relative_to(install_dir.resolve()):
            return
    except (OSError, ValueError):
        pass
    for name in [name for name in sys.modules if name == "src" or name.startswith("src.")]:
        sys.modules.pop(name, None)


def _ensure_helmet_config_shim(install_dir: Path, entry: EngineEntry) -> None:
    """demo 缺少 YOLO11HelmetConfig.py：真实模块可导入则用真实的，否则注入 shim。"""
    module_name = "src.config.model.YOLO11HelmetConfig"
    try:
        importlib.import_module(module_name)
        return
    except ImportError:
        pass
    model_path = str((install_dir / entry.models[0]).resolve())

    class YOLO11InferConfig:
        """仿 demo 其它 *InferConfig 的用法：引擎只调 getCurrentHelmetDetectionModelPath()。"""

        @staticmethod
        def getCurrentHelmetDetectionModelPath() -> str:  # noqa: N802  # 与真实配置类同接口
            return model_path

    shim = types.ModuleType(module_name)
    shim.YOLO11InferConfig = YOLO11InferConfig  # type: ignore[attr-defined]
    sys.modules[module_name] = shim
    logger.info("已注入 %s shim（model_path=%s）", module_name, model_path)


def _install_face_stubs() -> None:
    """face 引擎的 ES/MinIO 识别链路在本项目不用，注入桩使其可导入且不连外部服务。"""
    # 第三方库桩：仅当真实包未安装时注入，避免遮蔽真实依赖
    for name in (
        "elasticsearch",
        "elasticsearch_dsl",
        "minio",
        "minio.datatypes",
        "minio.deleteobjects",
        "minio.helpers",
        "aiohttp",  # src.util.ImageUtil 顶层 import（异步取图函数本项目不调用）
    ):
        if name in sys.modules:
            continue
        try:
            found = importlib.util.find_spec(name) is not None
        except (ImportError, ValueError):
            found = False
        if not found:
            sys.modules[name] = types.ModuleType(name)

    # flask 桩：src.config.InitLogger 顶层 `from flask import request`（仅日志用），
    # 桩模块需提供 request 属性使 import 成功
    if "flask" not in sys.modules:
        try:
            flask_found = importlib.util.find_spec("flask") is not None
        except (ImportError, ValueError):
            flask_found = False
        if not flask_found:
            flask_stub = types.ModuleType("flask")
            flask_stub.request = None  # type: ignore[attr-defined]
            sys.modules["flask"] = flask_stub

    # src.base 桩：真实模块在 import 时即连接 ES/MinIO，始终替换（确定性行为）。
    # retrievalByFeature 返回 scoreEmpty=True，引擎异步识别落入“陌生人”分支，minio 上传不会触发。
    fv_module = types.ModuleType("src.base.ESHandler.FaceFeatureVectorHandler")

    class _EmptySearchResult:
        scoreEmpty = True  # noqa: N815  # 与真实检索结果 VO 字段同名
        searchResults: list[Any] = []  # noqa: N815

    class FeatureVectorHandler:  # noqa: D101  # 与真实类同名同静态接口
        @staticmethod
        def retrievalByFeature(**_kwargs: Any) -> _EmptySearchResult:  # noqa: N802  # 与真实类同接口
            return _EmptySearchResult()

    fv_module.FeatureVectorHandler = FeatureVectorHandler  # type: ignore[attr-defined]
    sys.modules[fv_module.__name__] = fv_module

    minio_module = types.ModuleType("src.base.minio.MinioPySDK")
    minio_module.minioClient = types.SimpleNamespace(  # type: ignore[attr-defined]
        _secure=False,
        _serverUrl="",
        uploadImageByStream=lambda **_kwargs: None,
    )
    sys.modules[minio_module.__name__] = minio_module

    # 门禁控制桩：door_controller 顶层 import paho.mqtt（开门联动，本项目不用）；
    # 桩掉后 ES 空结果分支也永远不会触发 door_control
    door_module = types.ModuleType("src.service.stream_infer.door_controller")
    door_module.door_control = lambda *_args, **_kwargs: None  # type: ignore[attr-defined]
    sys.modules[door_module.__name__] = door_module


# 整包 inference.yaml 的 (节, 键) → 安装目录根级 onnx 文件名映射。
# 引擎 import 链上的配置单例可能读取引擎自身之外的节（如 head 引擎会读
# person_detection.yolov8），zip 自带 demo 整包 yaml 时需把已安装文件的路径一并重写。
_MODEL_PATH_REMAP = {
    ("face_detection", "retinaface"): "retinaface_mobilenet0.25.onnx",
    ("face_feat_ext", "arcface"): "arcface_finetune.onnx",
    ("keyPoint", "hrnet"): "dark_hrnet.onnx",
    # kpt 引擎的 YOLOInferenceConfig 硬编码读 yolov4 键（实为 yolov8 模型）
    ("person_detection", "yolov4"): "yolov8.onnx",
    ("person_detection", "yolov8"): "yolov8.onnx",
    ("headCount", "yolov8"): "models.onnx",
    ("helmet", "yolov11"): "helmet_v6.onnx",
    ("smoke", "yolo26"): "yolov26_1126.onnx",
}


def _write_inference_yaml(entry: EngineEntry, install_dir: Path) -> None:
    """在引擎目录生成/合并 resource/inference.yaml（配置类相对自身文件定位到此）。

    zip 自带 demo 整包 yaml 时在其基础上合并：引擎自身节整体覆盖为绝对路径，
    其它节中已安装 onnx 的旧路径（/workspace/...）同步重映射，避免 import 链上的
    配置单例读到不存在的路径。
    """
    resource_dir = install_dir / "resource"
    resource_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = resource_dir / "inference.yaml"
    config: dict[str, Any] = {}
    if yaml_path.is_file():
        with open(yaml_path, encoding="utf-8") as fp:
            loaded = yaml.safe_load(fp)
            if isinstance(loaded, dict):
                config = loaded
    model_config = config.setdefault("inference", {}).setdefault("model", {})
    models = {name: (install_dir / name).resolve() for name in entry.models}
    model_config.update(_YAML_BUILDERS[entry.kind](models))
    for (section, key), filename in _MODEL_PATH_REMAP.items():
        file_path = install_dir / filename
        block = model_config.get(section, {}).get(key) if isinstance(model_config.get(section), dict) else None
        if isinstance(block, dict) and file_path.is_file():
            block["model_path"] = str(file_path.resolve())
    with open(yaml_path, "w", encoding="utf-8") as fp:
        yaml.safe_dump(config, fp, allow_unicode=True, sort_keys=False)


def _model_block(path: Path, **extra: Any) -> dict[str, Any]:
    """与 demo inference.yaml 中模型块同构；resource_type 仅为占位，providers 由引擎写死。"""
    return {
        "model_path": str(path),
        "model_precision": "float32",
        "execute_threads": 8,
        "resource_type": "CPU",
        "device_id": 0,
        **extra,
    }


def _yaml_face(models: dict[str, Path]) -> dict[str, Any]:
    return {
        "face_detection": {
            "model_type": "retinaface",
            "supported_model": ["retinaface"],
            "retinaface": _model_block(models["retinaface_mobilenet0.25.onnx"]),
        },
        "face_feat_ext": {
            "model_type": "arcface",
            "supported_model": ["facenet", "arcface"],
            # bucket/object 键仅供引擎 minio 上传路径读取（本项目已桩掉，不生效）
            "arcface": _model_block(
                models["arcface_finetune.onnx"],
                bucketName="zhcs",
                face_object_name="open_door/stranger/face",
                body_object_name="open_door/stranger/body",
                object_name="face_stream_cropped_images/gallery",
            ),
        },
    }


def _yaml_head(models: dict[str, Path]) -> dict[str, Any]:
    return {
        "headCount": {
            "model_type": "yolov8",
            "supported_model": ["yolov8"],
            "yolov8": _model_block(models["models.onnx"]),
        }
    }


def _yaml_helmet(models: dict[str, Path]) -> dict[str, Any]:
    # helmet 引擎实际走 sys.modules shim 配置，此处仅为保持目录结构完整
    return {
        "helmet": {
            "model_type": "yolov11",
            "supported_model": ["yolov11"],
            "yolov11": _model_block(models["helmet_v6.onnx"]),
        }
    }


def _yaml_kpt(models: dict[str, Path]) -> dict[str, Any]:
    # YOLOInferenceConfig 把检测模型路径写死读 person_detection.yolov4 键（实为 yolov8 模型）
    yolov8_block = _model_block(models["yolov8.onnx"])
    return {
        "person_detection": {
            "model_type": "yolov8",
            "supported_model": ["yolov4", "yolov8"],
            "yolov4": yolov8_block,
            "yolov8": dict(yolov8_block),
        },
        "keyPoint": {
            "model_type": "hrnet",
            "supported_model": ["hrnet"],
            "hrnet": _model_block(models["dark_hrnet.onnx"]),
        },
    }


def _yaml_smoke(models: dict[str, Path]) -> dict[str, Any]:
    # YOLO26SmokeConfig 取 supported_model[1] 作为当前模型，必须保持 [yolo11, yolo26] 顺序
    return {
        "smoke": {
            "model_type": "yolo26",
            "supported_model": ["yolo11", "yolo26"],
            "yolo26": _model_block(models["yolov26_1126.onnx"]),
        }
    }


_YAML_BUILDERS = {
    "face": _yaml_face,
    "head": _yaml_head,
    "helmet": _yaml_helmet,
    "kpt": _yaml_kpt,
    "smoke": _yaml_smoke,
}

_engine_cache: dict[str, tuple[AlgorithmSpec, Any]] = {}
_cache_lock = threading.Lock()
