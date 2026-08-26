"""stream_manager 可测纯逻辑：识别冷却与 legacy 目标回退，重活（拉流/推理）不在此覆盖。"""

from uuid import uuid4

from app.config import Settings
from app.schemas import StreamStartRequest
from app.stream_manager import StreamManager


def make_manager() -> StreamManager:
    return StreamManager(settings=Settings(), face_client=object(), dino_client=None)


def test_due_face_targets_applies_recognition_cooldown():
    manager = make_manager()
    request = StreamStartRequest(
        cameraId=uuid4(),
        cameraName="北门",
        streamUrl="rtsp://camera/live",
        faceProfileId=uuid4(),
    )

    first = manager._due_face_targets(request, now=1000.0)
    second = manager._due_face_targets(request, now=1000.5)

    assert len(first) == 1
    assert first[0].faceProfileId == request.faceProfileId
    assert second == []


def test_face_targets_falls_back_to_legacy_face_profile_id():
    manager = make_manager()
    deployment_task_id = uuid4()
    request = StreamStartRequest(
        cameraId=uuid4(),
        cameraName="北门",
        streamUrl="rtsp://camera/live",
        faceProfileId=uuid4(),
        deploymentTaskId=deployment_task_id,
    )

    targets = manager._face_targets(request)

    assert len(targets) == 1
    assert targets[0].faceProfileId == request.faceProfileId
    assert targets[0].deploymentTaskId == deployment_task_id
