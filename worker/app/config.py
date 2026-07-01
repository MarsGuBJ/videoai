from functools import lru_cache
from pydantic import BaseModel
import os


class Settings(BaseModel):
    backend_internal_url: str = os.getenv("BACKEND_INTERNAL_URL", "http://localhost:8081")
    triton_http_url: str = os.getenv("TRITON_HTTP_URL", "http://localhost:8000")
    scrfd_model_name: str = os.getenv("SCRFD_MODEL_NAME", "scrfd_10g")
    arcface_model_name: str = os.getenv("ARCFACE_MODEL_NAME", "arcface_mbf")
    face_match_threshold: float = float(os.getenv("FACE_MATCH_THRESHOLD", "0.55"))
    face_event_cooldown_seconds: int = int(os.getenv("FACE_EVENT_COOLDOWN_SECONDS", "10"))
    frame_sample_fps: float = float(os.getenv("FRAME_SAMPLE_FPS", "2"))
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


@lru_cache
def settings() -> Settings:
    return Settings()
