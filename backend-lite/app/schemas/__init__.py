"""DTO 包：全部请求/响应 schema 统一出口。"""

from app.schemas.camera import CameraResponse
from app.schemas.deployment_task import (
    DeploymentTaskCreateRequest,
    DeploymentTaskResponse,
    DeploymentTaskUpdateRequest,
)
from app.schemas.event import (
    FaceEventIngestRequest,
    FaceEventResponse,
    FaceMatchEventResponse,
    ObjectEventIngestRequest,
    ObjectEventResponse,
    ObjectInfo,
)
from app.schemas.event_dedup_rule import DedupRuleCreate, DedupRuleOut, DedupRuleUpdate
from app.schemas.event_info import EventAttrItem, EventInfoCreate, EventInfoOut, EventInfoUpdate
from app.schemas.event_push_task import PushTaskCreate, PushTaskOut, PushTaskUpdate
from app.schemas.face import (
    FaceProfileResponse,
    FaceScanSummary,
    FaceUploadRequest,
    MatchRequest,
    MatchResponse,
)
from app.schemas.health import HealthResponse
from app.schemas.llm_config import LlmConfigCreate, LlmConfigOut, LlmConfigUpdate, LlmTestResult
from app.schemas.model import (
    ModelGpuResponse,
    ModelGpuUpdateRequest,
    ModelRegisterRequest,
    ModelResponse,
)
from app.schemas.person_search import (
    PersonSearchByBboxRequest,
    PersonSearchDetectRequest,
    PersonSearchImageResponse,
    TextSearchQueryRequest,
)
from app.schemas.windows_camera import WindowsCameraStartRequest, WindowsCameraStatus

__all__ = [
    "CameraResponse",
    "DedupRuleCreate",
    "DedupRuleOut",
    "DedupRuleUpdate",
    "DeploymentTaskCreateRequest",
    "DeploymentTaskResponse",
    "DeploymentTaskUpdateRequest",
    "EventAttrItem",
    "EventInfoCreate",
    "EventInfoOut",
    "EventInfoUpdate",
    "FaceEventIngestRequest",
    "FaceEventResponse",
    "FaceMatchEventResponse",
    "FaceProfileResponse",
    "FaceScanSummary",
    "FaceUploadRequest",
    "HealthResponse",
    "LlmConfigCreate",
    "LlmConfigOut",
    "LlmConfigUpdate",
    "LlmTestResult",
    "MatchRequest",
    "MatchResponse",
    "ModelGpuResponse",
    "ModelGpuUpdateRequest",
    "ModelRegisterRequest",
    "ModelResponse",
    "ObjectEventIngestRequest",
    "ObjectEventResponse",
    "ObjectInfo",
    "PersonSearchByBboxRequest",
    "PersonSearchDetectRequest",
    "PersonSearchImageResponse",
    "PushTaskCreate",
    "PushTaskOut",
    "PushTaskUpdate",
    "TextSearchQueryRequest",
    "WindowsCameraStartRequest",
    "WindowsCameraStatus",
]
