"""Worker configuration via pydantic-settings: env vars (uppercase field names) override defaults."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 内网地址等默认值与原有 os.getenv 缺省一致，均可用同名大写环境变量覆盖
    backend_internal_url: str = "http://localhost:8081"
    # 本 worker HTTP 服务端口（见 Dockerfile CMD/EXPOSE 8090），心跳上报用
    worker_port: int = 8090
    # GPU 监控心跳周期（秒）
    monitor_interval_seconds: int = 10
    # 监控节点标识与上报 IP：默认空 = 用 socket 主机名/自动探测。
    # 容器重建后主机名（容器 ID）会变，监控页会出现多个同 IP 的离线节点；
    # 生产环境用 WORKER_NODE_NAME / WORKER_NODE_IP 固定
    worker_node_name: str = ""
    worker_node_ip: str = ""
    triton_http_url: str = "http://localhost:8000"
    face_detector: str = "scrfd"
    scrfd_model_name: str = "scrfd_10g"
    retinaface_model_name: str = "retinaface_mobilenet"
    retinaface_input_name: str = "input"
    retinaface_loc_output: str = "loc"
    retinaface_cls_output: str = "cls"
    retinaface_land_output: str = "land"
    retinaface_score_threshold: float = 0.5
    arcface_model_name: str = "arcface_mbf"
    face_match_threshold: float = 0.55
    face_event_cooldown_seconds: int = 10
    frame_sample_fps: float = 0
    scrfd_input_name: str = "input.1"
    scrfd_score_8_output: str = "448"
    scrfd_score_16_output: str = "471"
    scrfd_score_32_output: str = "494"
    scrfd_bbox_8_output: str = "451"
    scrfd_bbox_16_output: str = "474"
    scrfd_bbox_32_output: str = "497"
    scrfd_kps_8_output: str = "454"
    scrfd_kps_16_output: str = "477"
    scrfd_kps_32_output: str = "500"
    arcface_input_name: str = "input.1"
    arcface_output_name: str = "516"
    dino_triton_http_url: str = "http://192.168.11.194:8003"
    dino_model_name: str = "dino_coco"
    dino_image_input: str = "image"
    dino_imshape_input: str = "im_shape"
    dino_scalefactor_input: str = "scale_factor"
    dino_output_0: str = "save_infer_model/scale_0.tmp_0"
    dino_output_1: str = "save_infer_model/scale_1.tmp_0"
    dino_conf_thres: float = 0.3
    dino_labels: list[str] = [
        "person",
        "bicycle",
        "car",
        "motorcycle",
        "airplane",
        "bus",
        "train",
        "truck",
        "boat",
        "traffic light",
        "fire hydrant",
        "stop sign",
        "parking meter",
        "bench",
        "bird",
        "cat",
        "dog",
        "horse",
        "sheep",
        "cow",
        "elephant",
        "bear",
        "zebra",
        "giraffe",
        "backpack",
        "umbrella",
        "handbag",
        "tie",
        "suitcase",
        "frisbee",
        "skis",
        "snowboard",
        "sports ball",
        "kite",
        "baseball bat",
        "baseball glove",
        "skateboard",
        "surfboard",
        "tennis racket",
        "bottle",
        "wine glass",
        "cup",
        "fork",
        "knife",
        "spoon",
        "bowl",
        "banana",
        "apple",
        "sandwich",
        "orange",
        "broccoli",
        "carrot",
        "hot dog",
        "pizza",
        "donut",
        "cake",
        "chair",
        "couch",
        "potted plant",
        "bed",
        "dining table",
        "toilet",
        "tv",
        "laptop",
        "mouse",
        "remote",
        "keyboard",
        "cell phone",
        "microwave",
        "oven",
        "toaster",
        "sink",
        "refrigerator",
        "book",
        "clock",
        "vase",
        "scissors",
        "teddy bear",
        "hair drier",
        "toothbrush",
    ]
    dino_target_size: list[int] = [800, 1333]
    dino_mean: list[float] = [0.485, 0.456, 0.406]
    dino_std: list[float] = [0.229, 0.224, 0.225]
    object_detection_enabled: bool = True
    # backend-lite 解压安装算法引擎 zip 的共享目录（<dir>/<code>/<version>/）
    algorithms_dir: str = Field(default="/data/algorithms", validation_alias="VIDEOAI_STORAGE_ALGORITHM_DIR")

    @field_validator("face_detector")
    @classmethod
    def _normalize_face_detector(cls, value: str) -> str:
        # 与原 os.getenv("FACE_DETECTOR", "scrfd").lower() 语义一致
        return value.lower()

    @field_validator("object_detection_enabled", mode="before")
    @classmethod
    def _parse_object_detection_enabled(cls, value):
        # 与原 os.getenv(...).lower() == "true" 语义一致：仅 "true"（忽略大小写）为 True
        if isinstance(value, str):
            return value.lower() == "true"
        return value


@lru_cache
def settings() -> Settings:
    """Return the process-wide cached Settings instance."""
    return Settings()
