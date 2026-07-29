from functools import lru_cache
from pydantic import BaseModel
import os


class Settings(BaseModel):
    backend_internal_url: str = os.getenv("BACKEND_INTERNAL_URL", "http://localhost:8081")
    triton_http_url: str = os.getenv("TRITON_HTTP_URL", "http://localhost:8000")
    face_detector: str = os.getenv("FACE_DETECTOR", "scrfd").lower()
    scrfd_model_name: str = os.getenv("SCRFD_MODEL_NAME", "scrfd_10g")
    retinaface_model_name: str = os.getenv("RETINAFACE_MODEL_NAME", "retinaface_mobilenet")
    retinaface_input_name: str = os.getenv("RETINAFACE_INPUT_NAME", "input")
    retinaface_loc_output: str = os.getenv("RETINAFACE_LOC_OUTPUT", "loc")
    retinaface_cls_output: str = os.getenv("RETINAFACE_CLS_OUTPUT", "cls")
    retinaface_land_output: str = os.getenv("RETINAFACE_LAND_OUTPUT", "land")
    retinaface_score_threshold: float = float(os.getenv("RETINAFACE_SCORE_THRESHOLD", "0.5"))
    arcface_model_name: str = os.getenv("ARCFACE_MODEL_NAME", "arcface_mbf")
    face_match_threshold: float = float(os.getenv("FACE_MATCH_THRESHOLD", "0.55"))
    face_event_cooldown_seconds: int = int(os.getenv("FACE_EVENT_COOLDOWN_SECONDS", "10"))
    frame_sample_fps: float = float(os.getenv("FRAME_SAMPLE_FPS", "0"))
    scrfd_input_name: str = os.getenv("SCRFD_INPUT_NAME", "input.1")
    scrfd_score_8_output: str = os.getenv("SCRFD_SCORE_8_OUTPUT", "448")
    scrfd_score_16_output: str = os.getenv("SCRFD_SCORE_16_OUTPUT", "471")
    scrfd_score_32_output: str = os.getenv("SCRFD_SCORE_32_OUTPUT", "494")
    scrfd_bbox_8_output: str = os.getenv("SCRFD_BBOX_8_OUTPUT", "451")
    scrfd_bbox_16_output: str = os.getenv("SCRFD_BBOX_16_OUTPUT", "474")
    scrfd_bbox_32_output: str = os.getenv("SCRFD_BBOX_32_OUTPUT", "497")
    scrfd_kps_8_output: str = os.getenv("SCRFD_KPS_8_OUTPUT", "454")
    scrfd_kps_16_output: str = os.getenv("SCRFD_KPS_16_OUTPUT", "477")
    scrfd_kps_32_output: str = os.getenv("SCRFD_KPS_32_OUTPUT", "500")
    arcface_input_name: str = os.getenv("ARCFACE_INPUT_NAME", "input.1")
    arcface_output_name: str = os.getenv("ARCFACE_OUTPUT_NAME", "516")
    dino_triton_http_url: str = os.getenv("DINO_TRITON_HTTP_URL", "http://192.168.11.194:8003")
    dino_model_name: str = os.getenv("DINO_MODEL_NAME", "dino_coco")
    dino_image_input: str = os.getenv("DINO_IMAGE_INPUT", "image")
    dino_imshape_input: str = os.getenv("DINO_IMSHAPE_INPUT", "im_shape")
    dino_scalefactor_input: str = os.getenv("DINO_SCALEFACTOR_INPUT", "scale_factor")
    dino_output_0: str = os.getenv("DINO_OUTPUT_0", "save_infer_model/scale_0.tmp_0")
    dino_output_1: str = os.getenv("DINO_OUTPUT_1", "save_infer_model/scale_1.tmp_0")
    dino_conf_thres: float = float(os.getenv("DINO_CONF_THRES", "0.3"))
    dino_labels: list = [
        "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck",
        "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
        "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra",
        "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
        "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
        "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
        "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
        "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
        "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
        "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
        "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
        "hair drier", "toothbrush",
    ]
    dino_target_size: list = [800, 1333]
    dino_mean: list = [0.485, 0.456, 0.406]
    dino_std: list = [0.229, 0.224, 0.225]
    object_detection_enabled: bool = os.getenv("OBJECT_DETECTION_ENABLED", "true").lower() == "true"


@lru_cache
def settings() -> Settings:
    return Settings()
