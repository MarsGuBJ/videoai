"""stream_manager 可测纯逻辑：识别冷却与 legacy 目标回退，重活（拉流/推理）不在此覆盖。"""

import io
import time
from uuid import uuid4

from app.config import Settings
from app.schemas import AlgorithmSpec, StreamStartRequest
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


def test_due_face_targets_interval_is_seconds():
    """recognitionPerMinute 字段语义为采样间隔秒数：设置 x 则每 x 秒到期一次。"""
    from app.schemas import FaceTarget

    manager = make_manager()
    request = StreamStartRequest(
        cameraId=uuid4(),
        cameraName="北门",
        streamUrl="rtsp://camera/live",
        faceTargets=[FaceTarget(faceProfileId=uuid4(), recognitionPerMinute=10)],
    )

    assert len(manager._due_face_targets(request, now=1000.0)) == 1
    assert manager._due_face_targets(request, now=1009.9) == []
    assert len(manager._due_face_targets(request, now=1010.0)) == 1


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


def test_algorithm_specs_merge_and_dedup():
    """algorithms 与旧字段 algorithm 合并去重：同摄像头并行多算法（如 face + helmet）。"""
    legacy = AlgorithmSpec(algorithmId=uuid4(), engineType="face", version="1.0.0", installPath="/a")
    helmet = AlgorithmSpec(algorithmId=uuid4(), engineType="helmet", version="1.0.0", installPath="/b")
    request = StreamStartRequest(
        cameraId=uuid4(),
        cameraName="走廊",
        streamUrl="rtsp://camera/live",
        algorithm=legacy,
        algorithms=[helmet, helmet.model_copy()],
    )

    assert request.algorithm_specs == [helmet, legacy]


def test_process_frame_runs_algorithms_when_no_face_target_due(monkeypatch):
    """人脸采样未到期不再整帧早退：并行算法（安全帽检测）仍按各自限频执行。"""
    manager = make_manager()
    request = StreamStartRequest(
        cameraId=uuid4(),
        cameraName="走廊",
        streamUrl="rtsp://camera/live",
        faceProfileId=uuid4(),
        algorithms=[
            AlgorithmSpec(algorithmId=uuid4(), engineType="helmet", version="1.0.0", installPath="/b")
        ],
    )
    # 预置人脸采样冷却，模拟“人脸目标未到期”分支
    manager._due_face_targets(request, time.monotonic())

    calls: list[str] = []
    monkeypatch.setattr(
        manager, "_process_algorithm_frame", lambda req, spec, frame: calls.append(spec.engineType)
    )

    manager._process_frame(request, frame=None)

    assert calls == ["helmet"]


class _FakeOpenCvCapture:
    """能打开但永远读不出帧的 OpenCV 伪装（模拟 H.265 无 HEVC 解封装）。"""

    opened_count = 0

    def __init__(self, url: str):
        type(self).opened_count += 1

    def isOpened(self):
        return True

    def read(self):
        return False, None

    def release(self):
        pass


class _NeverOpenCapture:
    def __init__(self, url: str):
        pass

    def isOpened(self):
        return False

    def release(self):
        pass


class _FakePipeProc:
    """ffmpeg 管道伪装：预置若干帧；dead=True 模拟进程已退出。"""

    def __init__(self, frames: list[bytes], dead: bool = False):
        self.stdout = io.BytesIO(b"".join(frames))
        self.dead = dead
        self.killed = False

    def poll(self):
        return 1 if self.dead else None

    def kill(self):
        self.killed = True


def _wait_for(predicate, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def test_opencv_no_frames_switches_to_ffmpeg_pipe(monkeypatch):
    """H.265 场景：isOpened() 正常、read() 永远失败 → 重开限次后强制走 ffmpeg 管道并出帧。"""
    import app.stream_manager as sm

    monkeypatch.setattr(sm, "CAPTURE_RETRY_INTERVAL_SECONDS", 0.05)
    monkeypatch.setattr(sm.cv2, "VideoCapture", _FakeOpenCvCapture)
    _FakeOpenCvCapture.opened_count = 0

    manager = make_manager()
    pipe_calls: list[str] = []
    pipe_frames = [b"\x01" * (1920 * 1080 * 3)] * 8

    def fake_start(url: str):
        pipe_calls.append(url)
        return _FakePipeProc(pipe_frames)

    monkeypatch.setattr(manager, "_start_ffmpeg_pipe", fake_start)

    request = StreamStartRequest(
        cameraId=uuid4(),
        cameraName="HEVC摄像头",
        streamUrl="http://zlm/live/x.live.flv",
        faceDetectionEnabled=False,
        objectDetectionEnabled=False,
    )
    manager.start(request)
    try:
        assert _wait_for(lambda: len(pipe_calls) >= 1), "OpenCV 持续无帧后应启动 ffmpeg 兜底管道"
        assert _FakeOpenCvCapture.opened_count <= sm.OPENCV_MAX_RECOVERY_ATTEMPTS + 1
        assert _wait_for(lambda: manager.status().get(str(request.cameraId)) == "running")
    finally:
        manager.stop(request.cameraId)


def test_ffmpeg_pipe_exit_reconnects_and_retries(monkeypatch):
    """管道退出（poll 非 None）→ 状态 reconnecting，并按冷却间隔重建新管道。"""
    import app.stream_manager as sm

    monkeypatch.setattr(sm, "CAPTURE_RETRY_INTERVAL_SECONDS", 0.05)
    monkeypatch.setattr(sm.cv2, "VideoCapture", _NeverOpenCapture)

    manager = make_manager()
    procs: list[_FakePipeProc] = []

    def fake_start(url: str):
        proc = _FakePipeProc([], dead=True)
        procs.append(proc)
        return proc

    monkeypatch.setattr(manager, "_start_ffmpeg_pipe", fake_start)

    request = StreamStartRequest(
        cameraId=uuid4(),
        cameraName="HEVC摄像头",
        streamUrl="http://zlm/live/x.live.flv",
        faceDetectionEnabled=False,
        objectDetectionEnabled=False,
    )
    manager.start(request)
    try:
        assert _wait_for(lambda: manager.status().get(str(request.cameraId)) == "reconnecting")
        assert _wait_for(lambda: len(procs) >= 2), "管道退出后应按冷却间隔持续重建"
    finally:
        manager.stop(request.cameraId)
