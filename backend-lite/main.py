from datetime import datetime, timezone
import base64
import json
import logging
import math
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request as UrlRequest, urlopen
from uuid import UUID, uuid4

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


SRS_HTTP_URL = os.getenv("VIDEOAI_ZLM_HTTP_URL", os.getenv("SRS_HTTP_URL", "http://localhost:8080")).rstrip("/")
SRS_PUBLIC_HTTP_URL = os.getenv("VIDEOAI_ZLM_PUBLIC_HTTP_URL", os.getenv("ZLM_PUBLIC_HTTP_URL", SRS_HTTP_URL)).rstrip("/")
ZLM_SECRET = os.getenv("VIDEOAI_ZLM_SECRET", os.getenv("ZLM_SECRET", "035c73f7-bb6b-4889-a715-d9eb2d1925cc")).strip()
WORKER_URL = os.getenv("VIDEOAI_WORKER_URL", os.getenv("WORKER_URL", "http://localhost:8090")).rstrip("/")
FFMPEG_BIN = os.getenv("FFMPEG_BIN", "ffmpeg")
WINDOWS_FFMPEG_BIN = os.getenv("WINDOWS_FFMPEG_BIN", "ffmpeg")
WINDOWS_CAMERA_NAME = os.getenv("WINDOWS_CAMERA_NAME", "Surface Camera Front")
WINDOWS_CAMERA_STREAM = os.getenv("WINDOWS_CAMERA_STREAM", "win_camera")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
FACE_STORAGE_DIR = Path(os.getenv("VIDEOAI_STORAGE_FACE_DIR", str(PROJECT_ROOT / "storage" / "faces")))
SNAPSHOT_STORAGE_DIR = Path(os.getenv("VIDEOAI_STORAGE_SNAPSHOT_DIR", str(PROJECT_ROOT / "storage" / "snapshots")))
FACE_METADATA_FILE = FACE_STORAGE_DIR / "faces.json"
FACE_EMBEDDINGS_FILE = FACE_STORAGE_DIR / "face_embeddings.json"
FACE_SCAN_ENABLED = os.getenv("FACE_SCAN_ENABLED", "false").lower() != "false"
FACE_SCAN_INTERVAL_SECONDS = int(os.getenv("FACE_SCAN_INTERVAL_SECONDS", "300"))
FACE_SCAN_INITIAL_DELAY_SECONDS = int(os.getenv("FACE_SCAN_INITIAL_DELAY_SECONDS", "10"))
FACE_SCAN_TIMEOUT_SECONDS = int(os.getenv("FACE_SCAN_TIMEOUT_SECONDS", "15"))
FACE_MATCH_THRESHOLD = float(os.getenv("FACE_MATCH_THRESHOLD", "0.45"))
FACE_EVENT_COOLDOWN_SECONDS = int(os.getenv("FACE_EVENT_COOLDOWN_SECONDS", "60"))
TRITON_HTTP_URL = os.getenv("TRITON_HTTP_URL", "http://localhost:8000").rstrip("/")
TRITON_MODEL_REPOSITORY = Path(os.getenv("TRITON_MODEL_REPOSITORY", str(PROJECT_ROOT / "infra" / "model_repository")))


class CameraCreateRequest(BaseModel):
    name: str
    sourceUrl: str
    description: Optional[str] = None
    area: Optional[str] = None
    nvrId: Optional[str] = None
    nvrChannel: Optional[str] = None
    nvrTrackId: Optional[str] = None
    nvrStreamType: Optional[str] = None


class CameraUpdateRequest(BaseModel):
    name: Optional[str] = None
    sourceUrl: Optional[str] = None
    description: Optional[str] = None
    area: Optional[str] = None
    nvrId: Optional[str] = None
    nvrChannel: Optional[str] = None
    nvrTrackId: Optional[str] = None
    nvrStreamType: Optional[str] = None


class CameraResponse(BaseModel):
    id: UUID
    name: str
    sourceUrl: str
    streamApp: str
    streamName: str
    ffmpegKey: Optional[str] = None
    description: Optional[str] = None
    area: Optional[str] = None
    status: str
    playbackUrl: str
    createdAt: datetime
    updatedAt: datetime
    nvrId: Optional[str] = None
    nvrChannel: Optional[str] = None
    nvrTrackId: Optional[str] = None
    nvrStreamType: Optional[str] = None


class HealthResponse(BaseModel):
    status: str


class FaceProfileResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    photoUrl: str
    createdAt: datetime
    updatedAt: datetime


class FaceEventResponse(BaseModel):
    id: UUID
    cameraId: UUID
    faceProfileId: UUID
    cameraName: str
    profileName: str
    profileDescription: Optional[str] = None
    facePhotoUrl: str
    snapshotUrl: Optional[str] = None
    videoTime: datetime
    similarity: float
    createdAt: datetime


class FaceMatchEventResponse(BaseModel):
    id: UUID
    deploymentTaskId: Optional[UUID] = None
    faceProfileId: Optional[UUID] = None
    faceProfileName: Optional[str] = None
    faceProfilePhotoUrl: Optional[str] = None
    snapshotUrl: Optional[str] = None
    cameraId: Optional[UUID] = None
    cameraName: Optional[str] = None
    cameraArea: Optional[str] = None
    similarity: float
    matchedAt: datetime
    createdAt: datetime


class DeploymentTaskResponse(BaseModel):
    id: UUID
    name: str
    pipeline: str
    area: str
    areaCount: int
    enabled: bool
    taskStatus: str
    desc: str
    faceProfileId: Optional[UUID] = None
    faceProfileName: Optional[str] = None
    faceProfilePhotoUrl: Optional[str] = None
    cameraIds: List[str]
    createdAt: datetime
    updatedAt: datetime


class DeploymentTaskCreateRequest(BaseModel):
    name: str
    pipeline: str = "人脸识别流程"
    area: Optional[str] = None
    areaCount: int = 0
    enabled: bool = True
    desc: str = ""
    faceProfileId: Optional[UUID] = None
    faceProfileName: Optional[str] = None
    faceProfilePhotoUrl: Optional[str] = None
    cameraIds: List[str] = []


class DeploymentTaskUpdateRequest(BaseModel):
    name: Optional[str] = None
    pipeline: Optional[str] = None
    area: Optional[str] = None
    areaCount: Optional[int] = None
    enabled: Optional[bool] = None
    taskStatus: Optional[str] = None
    desc: Optional[str] = None
    faceProfileId: Optional[UUID] = None
    faceProfileName: Optional[str] = None
    faceProfilePhotoUrl: Optional[str] = None
    cameraIds: Optional[List[str]] = None


class FaceEventIngestRequest(BaseModel):
    cameraId: UUID
    faceProfileId: UUID
    cameraName: str
    profileName: str
    profileDescription: Optional[str] = None
    facePhotoPath: str
    snapshotBase64: Optional[str] = None
    videoTime: datetime
    similarity: float
    deploymentTaskId: Optional[UUID] = None


class ObjectInfo(BaseModel):
    labelId: int
    labelName: str
    score: float
    x1: float
    y1: float
    x2: float
    y2: float


class ObjectEventResponse(BaseModel):
    id: UUID
    cameraId: UUID
    cameraName: str
    objects: List[ObjectInfo]
    snapshotUrl: Optional[str] = None
    videoTime: datetime
    frameWidth: int = 0
    frameHeight: int = 0
    createdAt: datetime


class ObjectEventIngestRequest(BaseModel):
    cameraId: UUID
    cameraName: str
    objects: List[ObjectInfo]
    snapshotBase64: Optional[str] = None
    videoTime: datetime
    frameWidth: int = 0
    frameHeight: int = 0


class MatchRequest(BaseModel):
    embedding: List[float]
    threshold: Optional[float] = None
    faceProfileId: Optional[UUID] = None


class MatchResponse(BaseModel):
    matched: bool
    id: Optional[UUID] = None
    name: Optional[str] = None
    description: Optional[str] = None
    photoPath: Optional[str] = None
    similarity: float = 0.0


class FaceScanSummary(BaseModel):
    cameras: int
    faces: int
    framesCaptured: int
    faceDetections: int
    matches: int
    errors: List[str]
    scannedAt: datetime


class FaceUploadRequest(BaseModel):
    imageBase64: str
    name: Optional[str] = None
    cameraId: str
    modelName: str


class ModelRegisterRequest(BaseModel):
    name: str
    displayName: str
    repositoryPath: Optional[str] = None
    modelType: str
    description: Optional[str] = None


class ModelResponse(BaseModel):
    id: UUID
    name: str
    displayName: str
    repositoryPath: Optional[str] = None
    modelType: str
    description: Optional[str] = None
    state: str
    createdAt: datetime
    updatedAt: datetime


class EmptyModel(BaseModel):
    pass


class WindowsCameraStartRequest(BaseModel):
    deviceName: Optional[str] = None
    streamName: Optional[str] = None


class WindowsCameraStatus(BaseModel):
    available: bool
    running: bool
    ffmpegPath: Optional[str] = None
    deviceName: str
    streamName: str
    publishUrl: str
    devices: List[str]
    message: Optional[str] = None


app = FastAPI(title="VideoAI Lite Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

cameras: Dict[UUID, CameraResponse] = {}
faces_store: Dict[UUID, FaceProfileResponse] = {}
face_embeddings: Dict[UUID, List[float]] = {}
events_store: List[FaceEventResponse] = []
object_events_store: List[ObjectEventResponse] = []
deployment_tasks_store: Dict[UUID, DeploymentTaskResponse] = {}
object_event_cooldowns: Dict[str, float] = {}
event_subscribers: List[queue.Queue[str]] = []
event_lock = threading.Lock()
scanner_stop_event = threading.Event()
scanner_thread: Optional[threading.Thread] = None

proxy_guard_stop_event = threading.Event()

proxy_guard_thread: Optional[threading.Thread] = None
windows_camera_process: Optional[subprocess.Popen] = None
windows_camera_device = WINDOWS_CAMERA_NAME
windows_camera_stream = WINDOWS_CAMERA_STREAM
model_registry: Dict[str, ModelResponse] = {}
FACE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/api/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok")


@app.on_event("startup")
def start_face_scanner():
    global scanner_thread, proxy_guard_thread
    try:
        from db import Base, engine
        Base.metadata.create_all(engine)
    except Exception as exc:
        print(f"Base.metadata.create_all failed: {exc}", flush=True)
    load_faces_from_disk()
    load_face_embeddings()
    seed_model_registry()
    seed_cameras()
    seed_face_profiles()
    proxy_guard_stop_event.clear()
    proxy_guard_thread = threading.Thread(target=stream_proxy_guard_loop, daemon=True)
    proxy_guard_thread.start()
    if not FACE_SCAN_ENABLED:
        return
    scanner_stop_event.clear()
    scanner_thread = threading.Thread(target=face_scan_loop, daemon=True)
    scanner_thread.start()


@app.on_event("shutdown")
def stop_face_scanner():
    scanner_stop_event.set()
    if scanner_thread and scanner_thread.is_alive():
        scanner_thread.join(timeout=2)
    proxy_guard_stop_event.set()
    if proxy_guard_thread and proxy_guard_thread.is_alive():
        proxy_guard_thread.join(timeout=2)


@app.get("/api/cameras", response_model=List[CameraResponse])
def list_cameras():
    return sorted(cameras.values(), key=lambda item: item.createdAt, reverse=True)


@app.post("/api/cameras", response_model=CameraResponse)
def create_camera(request: CameraCreateRequest):
    camera_id = uuid4()
    now = datetime.now(timezone.utc)
    stream_name = stream_name_from_source(request.sourceUrl) or str(camera_id)
    camera = CameraResponse(
        id=camera_id,
        name=request.name,
        sourceUrl=request.sourceUrl,
        streamApp="live",
        streamName=stream_name,
        description=request.description,
        area=clean_optional(request.area) or "办公楼",
        status="STOPPED",
        playbackUrl=playback_url(request.sourceUrl, stream_name),
        createdAt=now,
        updatedAt=now,
        nvrId=clean_optional(request.nvrId),
        nvrChannel=clean_optional(request.nvrChannel),
        nvrTrackId=clean_optional(request.nvrTrackId),
        nvrStreamType=clean_optional(request.nvrStreamType),
    )
    cameras[camera_id] = camera
    return camera


@app.get("/api/cameras/{camera_id}", response_model=CameraResponse)
def get_camera(camera_id: UUID):
    return require_camera(camera_id)


@app.patch("/api/cameras/{camera_id}", response_model=CameraResponse)
def update_camera(camera_id: UUID, request: CameraUpdateRequest):
    old = require_camera(camera_id)
    stream_name = stream_name_from_source(request.sourceUrl) or old.streamName
    new_name = request.name if request.name is not None else old.name
    new_source_url = request.sourceUrl if request.sourceUrl is not None else old.sourceUrl
    new_description = request.description if request.description is not None else old.description
    new_area = request.area if request.area is not None else old.area
    updated = old.model_copy(
        update={
            "name": new_name,
            "sourceUrl": new_source_url,
            "description": new_description,
            "area": new_area,
            "nvrId": clean_optional(request.nvrId),
            "nvrChannel": clean_optional(request.nvrChannel),
            "nvrTrackId": clean_optional(request.nvrTrackId),
            "nvrStreamType": clean_optional(request.nvrStreamType),
            "streamName": stream_name,
            "playbackUrl": playback_url(new_source_url, stream_name),
            "updatedAt": datetime.now(timezone.utc),
        }
    )
    cameras[camera_id] = updated
    return updated


@app.delete("/api/cameras/{camera_id}")
def delete_camera(camera_id: UUID):
    camera = cameras.pop(camera_id, None)
    if camera:
        stop_worker_stream(camera_id)
        remove_zlmediakit_proxy(camera.streamName)
    return {}


@app.post("/api/cameras/{camera_id}/start", response_model=CameraResponse)
def start_camera(camera_id: UUID):
    camera = require_camera(camera_id)
    updated = camera.model_copy(update={"status": "RUNNING", "updatedAt": datetime.now(timezone.utc)})
    cameras[camera_id] = updated
    add_zlmediakit_proxy(updated.sourceUrl, updated.streamName)
    start_worker_stream(updated)
    return updated


@app.post("/api/cameras/{camera_id}/stop", response_model=CameraResponse)
def stop_camera(camera_id: UUID):
    camera = require_camera(camera_id)
    updated = camera.model_copy(update={"status": "STOPPED", "updatedAt": datetime.now(timezone.utc)})
    cameras[camera_id] = updated
    stop_worker_stream(camera_id)
    remove_zlmediakit_proxy(updated.streamName)
    return updated


@app.get("/api/deployment-tasks", response_model=List[DeploymentTaskResponse])
def list_deployment_tasks():
    return sorted(deployment_tasks_store.values(), key=lambda item: item.createdAt, reverse=True)


@app.post("/api/deployment-tasks", response_model=DeploymentTaskResponse)
def create_deployment_task(request: DeploymentTaskCreateRequest):
    task_id = uuid4()
    now = datetime.now(timezone.utc)
    task = DeploymentTaskResponse(
        id=task_id,
        name=request.name,
        pipeline=request.pipeline,
        area=clean_optional(request.area) or "默认区域",
        areaCount=max(0, int(request.areaCount or 0)),
        enabled=bool(request.enabled),
        taskStatus="stopped" if not request.enabled else "running",
        desc=request.desc or "",
        faceProfileId=request.faceProfileId,
        faceProfileName=clean_optional(request.faceProfileName),
        faceProfilePhotoUrl=clean_optional(request.faceProfilePhotoUrl),
        cameraIds=list(request.cameraIds or []),
        createdAt=now,
        updatedAt=now,
    )
    deployment_tasks_store[task_id] = task
    return task


@app.get("/api/deployment-tasks/{task_id}", response_model=DeploymentTaskResponse)
def get_deployment_task(task_id: UUID):
    return require_deployment_task(task_id)


@app.patch("/api/deployment-tasks/{task_id}", response_model=DeploymentTaskResponse)
def update_deployment_task(task_id: UUID, request: DeploymentTaskUpdateRequest):
    old = require_deployment_task(task_id)
    update_payload: dict = {"updatedAt": datetime.now(timezone.utc)}
    if request.name is not None:
        update_payload["name"] = request.name
    if request.pipeline is not None:
        update_payload["pipeline"] = request.pipeline
    if request.area is not None:
        update_payload["area"] = request.area
    elif "area" in request.model_fields_set and request.area is None:
        update_payload["area"] = ""
    if request.areaCount is not None:
        update_payload["areaCount"] = max(0, int(request.areaCount))
    if request.enabled is not None:
        update_payload["enabled"] = bool(request.enabled)
        if "taskStatus" not in request.model_fields_set:
            update_payload["taskStatus"] = "running" if request.enabled else "stopped"
    if request.taskStatus is not None:
        update_payload["taskStatus"] = request.taskStatus
    if request.desc is not None:
        update_payload["desc"] = request.desc
    if request.faceProfileId is not None or "faceProfileId" in request.model_fields_set:
        update_payload["faceProfileId"] = request.faceProfileId
    if request.faceProfileName is not None or "faceProfileName" in request.model_fields_set:
        update_payload["faceProfileName"] = clean_optional(request.faceProfileName)
    if request.faceProfilePhotoUrl is not None or "faceProfilePhotoUrl" in request.model_fields_set:
        update_payload["faceProfilePhotoUrl"] = clean_optional(request.faceProfilePhotoUrl)
    if request.cameraIds is not None:
        update_payload["cameraIds"] = list(request.cameraIds)
    updated = old.model_copy(update=update_payload)
    deployment_tasks_store[task_id] = updated
    return updated


@app.delete("/api/deployment-tasks/{task_id}")
def delete_deployment_task(task_id: UUID):
    task = deployment_tasks_store.pop(task_id, None)
    if not task:
        raise HTTPException(status_code=404, detail="Deployment task not found")
    return {"deleted": str(task_id)}


@app.get("/api/faces", response_model=List[FaceProfileResponse])
def faces():
    return sorted(faces_store.values(), key=lambda item: item.createdAt, reverse=True)


@app.post("/api/faces", response_model=FaceProfileResponse)
async def create_face(name: str = Form(...), description: str = Form(""), photo: UploadFile = File(...)):
    face_id = uuid4()
    now = datetime.now(timezone.utc)
    photo_url = await save_face_photo(face_id, photo)
    face = FaceProfileResponse(
        id=face_id,
        name=name,
        description=description or None,
        photoUrl=photo_url,
        createdAt=now,
        updatedAt=now,
    )
    faces_store[face_id] = face
    refresh_face_embedding(face)
    persist_faces()
    return face


@app.patch("/api/faces/{face_id}", response_model=FaceProfileResponse)
async def update_face(face_id: UUID, name: str = Form(...), description: str = Form(""), photo: Optional[UploadFile] = File(None)):
    face = require_face(face_id)
    photo_url = face.photoUrl
    if photo and photo.filename:
        delete_face_photo(photo_url)
        photo_url = await save_face_photo(face_id, photo)
    updated = face.model_copy(
        update={
            "name": name,
            "description": description or None,
            "photoUrl": photo_url,
            "updatedAt": datetime.now(timezone.utc),
        }
    )
    faces_store[face_id] = updated
    refresh_face_embedding(updated)
    persist_faces()
    return updated


@app.delete("/api/faces/{face_id}")
def delete_face(face_id: UUID):
    face = faces_store.pop(face_id, None)
    if face:
        delete_face_photo(face.photoUrl)
        face_embeddings.pop(face_id, None)
        persist_face_embeddings()
        persist_faces()
    return {}


@app.post("/api/faces/upload-base64")
def upload_face_base64(request: FaceUploadRequest):
    if not request.imageBase64:
        raise HTTPException(status_code=400, detail="imageBase64 is required")
    data = request.imageBase64
    if "," in data:
        data = data.split(",", 1)[1]
    try:
        raw = base64.b64decode(data, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid base64 image data")
    if not raw:
        raise HTTPException(status_code=400, detail="empty image data")

    for face in list(faces_store.values()):
        delete_face_photo(face.photoUrl)
        face_embeddings.pop(face.id, None)
        faces_store.pop(face.id, None)

    face_id = uuid4()
    now = datetime.now(timezone.utc)
    filename = f"{face_id}.jpg"
    path = FACE_STORAGE_DIR / filename
    path.write_bytes(raw)
    photo_url = f"/api/assets/faces/{filename}"
    face = FaceProfileResponse(
        id=face_id,
        name=request.name or "人脸库照片",
        description=None,
        photoUrl=photo_url,
        createdAt=now,
        updatedAt=now,
    )
    faces_store[face_id] = face
    refresh_face_embedding(face)
    persist_faces()
    return {"faceId": str(face_id)}


@app.get("/api/assets/faces/{filename}")
def face_asset(filename: str):
    path = (FACE_STORAGE_DIR / filename).resolve()
    if not str(path).startswith(str(FACE_STORAGE_DIR.resolve())) or not path.is_file():
        raise HTTPException(status_code=404, detail="Face photo not found")
    return FileResponse(path)


@app.get("/api/assets/snapshots/{filename}")
def snapshot_asset(filename: str):
    path = (SNAPSHOT_STORAGE_DIR / filename).resolve()
    if not str(path).startswith(str(SNAPSHOT_STORAGE_DIR.resolve())) or not path.is_file():
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return FileResponse(path)


@app.get("/api/events", response_model=List[FaceEventResponse])
def events(limit: int = 100):
    safe_limit = max(1, min(limit, 200))
    with event_lock:
        return events_store[:safe_limit]


@app.get("/api/events/match", response_model=List[FaceEventResponse])
def events_match(faceId: str = "", limit: int = 10):
    safe_limit = max(1, min(limit, 10))
    with event_lock:
        if faceId:
            filtered = [e for e in events_store if str(e.faceProfileId) == faceId]
        else:
            filtered = list(events_store)
        filtered.sort(key=lambda e: e.videoTime, reverse=True)
        return filtered[:safe_limit]


@app.get("/api/face-match-events", response_model=List[FaceMatchEventResponse])
def list_face_match_events(limit: int = 100):
    safe_limit = max(1, min(limit, 500))
    try:
        from db import SessionLocal
        from models import FaceMatchEventORM
        with SessionLocal() as pgdb:
            rows = (
                pgdb.query(FaceMatchEventORM)
                .order_by(FaceMatchEventORM.matched_at.desc())
                .limit(safe_limit)
                .all()
            )
            return [
                FaceMatchEventResponse(
                    id=row.id,
                    deploymentTaskId=row.deployment_task_id,
                    faceProfileId=row.face_profile_id,
                    faceProfileName=row.face_profile_name,
                    faceProfilePhotoUrl=row.face_profile_photo_url,
                    snapshotUrl=row.snapshot_url,
                    cameraId=row.camera_id,
                    cameraName=row.camera_name,
                    cameraArea=row.camera_area,
                    similarity=float(row.similarity or 0.0),
                    matchedAt=row.matched_at,
                    createdAt=row.created_at,
                )
                for row in rows
            ]
    except Exception as exc:
        print(f"face-match-events query failed: {exc}", flush=True)
        return []


@app.get("/api/events/stream")
def event_stream():
    subscriber: queue.Queue[str] = queue.Queue(maxsize=100)
    with event_lock:
        event_subscribers.append(subscriber)

    def generator():
        yield "event: ready\ndata: ok\n\n"
        try:
            while True:
                try:
                    yield subscriber.get(timeout=15)
                except queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            with event_lock:
                if subscriber in event_subscribers:
                    event_subscribers.remove(subscriber)

    return StreamingResponse(generator(), media_type="text/event-stream")


@app.post("/api/events/ingest", response_model=Optional[FaceEventResponse])
def ingest_event(request: FaceEventIngestRequest):
    return create_face_event(
        camera_id=request.cameraId,
        face_profile_id=request.faceProfileId,
        camera_name=request.cameraName,
        profile_name=request.profileName,
        profile_description=request.profileDescription,
        face_photo_url=request.facePhotoPath or require_face(request.faceProfileId).photoUrl,
        snapshot_base64=request.snapshotBase64,
        video_time=request.videoTime,
        similarity=request.similarity,
        deployment_task_id=request.deploymentTaskId,
    )


@app.post("/api/events/object-ingest", response_model=Optional[ObjectEventResponse])
def ingest_object_event(request: ObjectEventIngestRequest):
    camera_key = str(request.cameraId)
    now_ts = time.time()
    cooldown_key = f"{camera_key}:objects"
    with event_lock:
        last_time = object_event_cooldowns.get(cooldown_key, 0)
        if now_ts - last_time < 2.0:
            return None
        object_event_cooldowns[cooldown_key] = now_ts

    now = datetime.now(timezone.utc)
    event = ObjectEventResponse(
        id=uuid4(),
        cameraId=request.cameraId,
        cameraName=request.cameraName,
        objects=request.objects,
        snapshotUrl=save_snapshot(request.snapshotBase64),
        videoTime=request.videoTime,
        frameWidth=request.frameWidth,
        frameHeight=request.frameHeight,
        createdAt=now,
    )
    payload = f"event: object-event\ndata: {event.model_dump_json()}\n\n"
    with event_lock:
        object_events_store.insert(0, event)
        del object_events_store[200:]
        stale = []
        for subscriber in event_subscribers:
            try:
                subscriber.put_nowait(payload)
            except queue.Full:
                stale.append(subscriber)
        for subscriber in stale:
            if subscriber in event_subscribers:
                event_subscribers.remove(subscriber)
    return event


@app.get("/api/events/objects", response_model=List[ObjectEventResponse])
def object_events(limit: int = 100):
    safe_limit = max(1, min(limit, 200))
    with event_lock:
        return object_events_store[:safe_limit]


@app.post("/api/internal/match", response_model=MatchResponse)
def internal_match(request: MatchRequest):
    threshold = request.threshold if request.threshold is not None else FACE_MATCH_THRESHOLD
    best_face: Optional[FaceProfileResponse] = None
    best_similarity = -1.0

    if request.faceProfileId is not None:
        target_id = request.faceProfileId
        target_face = faces_store.get(target_id)
        target_embedding = face_embeddings.get(target_id)
        if target_face is None or target_embedding is None:
            return MatchResponse(matched=False, similarity=0.0)
        similarity = cosine_similarity(request.embedding, target_embedding)
        if similarity < threshold:
            return MatchResponse(matched=False, similarity=max(0.0, similarity))
        return MatchResponse(
            matched=True,
            id=target_face.id,
            name=target_face.name,
            description=target_face.description,
            photoPath=target_face.photoUrl,
            similarity=max(0.0, min(1.0, similarity)),
        )

    for face_id, stored_embedding in face_embeddings.items():
        face = faces_store.get(face_id)
        if face is None:
            continue
        similarity = cosine_similarity(request.embedding, stored_embedding)
        if similarity > best_similarity:
            best_similarity = similarity
            best_face = face
    if best_face is None or best_similarity < threshold:
        return MatchResponse(matched=False, similarity=max(0.0, best_similarity))
    return MatchResponse(
        matched=True,
        id=best_face.id,
        name=best_face.name,
        description=best_face.description,
        photoPath=best_face.photoUrl,
        similarity=max(0.0, min(1.0, best_similarity)),
    )


@app.post("/api/events/scan", response_model=FaceScanSummary)
def scan_events_now():
    return scan_running_cameras()


@app.get("/api/models")
def models() -> List[ModelResponse]:
    refresh_model_states()
    return sorted(model_registry.values(), key=lambda item: item.createdAt, reverse=True)


@app.post("/api/models/register", response_model=ModelResponse)
def register_model(request: ModelRegisterRequest):
    if not request.name.strip():
        raise HTTPException(status_code=400, detail="Model name is required")
    if not request.displayName.strip():
        raise HTTPException(status_code=400, detail="Display name is required")
    now = datetime.now(timezone.utc)
    current = model_registry.get(request.name)
    model = ModelResponse(
        id=current.id if current else uuid4(),
        name=request.name,
        displayName=request.displayName,
        repositoryPath=request.repositoryPath or f"/models/{request.name}",
        modelType=request.modelType,
        description=request.description or None,
        state=current.state if current else "UNKNOWN",
        createdAt=current.createdAt if current else now,
        updatedAt=now,
    )
    model_registry[request.name] = model
    refresh_model_states()
    return model_registry[request.name]


@app.post("/api/models/{model_name}/load", response_model=ModelResponse)
def load_model(model_name: str):
    require_model(model_name)
    triton_request(f"/v2/repository/models/{quote(model_name, safe='')}/load", method="POST", payload={})
    update_model_state(model_name, "LOADING")
    refresh_model_states()
    return model_registry[model_name]


@app.post("/api/models/{model_name}/unload", response_model=ModelResponse)
def unload_model(model_name: str):
    require_model(model_name)
    triton_request(f"/v2/repository/models/{quote(model_name, safe='')}/unload", method="POST", payload={})
    update_model_state(model_name, "UNLOADING")
    refresh_model_states()
    return model_registry[model_name]


@app.get("/api/models/{model_name}/config")
def model_config(model_name: str):
    require_model(model_name)
    config = triton_request(f"/v2/models/{quote(model_name, safe='')}/config", method="GET")
    return {"name": model_name, "config": config}


@app.get("/api/windows-camera/status", response_model=WindowsCameraStatus)
def windows_camera_status():
    return build_windows_camera_status()


@app.post("/api/windows-camera/start", response_model=WindowsCameraStatus)
def start_windows_camera(request: WindowsCameraStartRequest):
    global windows_camera_process, windows_camera_device, windows_camera_stream

    if not is_wsl_with_windows_tools():
        raise HTTPException(status_code=400, detail="Windows camera control is only available from WSL with powershell.exe")

    ffmpeg_path = find_windows_ffmpeg()
    if not ffmpeg_path:
        raise HTTPException(
            status_code=500,
            detail="Windows ffmpeg.exe not found. Install it with: winget install --id Gyan.FFmpeg -e",
        )

    if windows_camera_process and windows_camera_process.poll() is None:
        return build_windows_camera_status()

    windows_camera_device = request.deviceName or windows_camera_device
    windows_camera_stream = request.streamName or windows_camera_stream
    publish_url = windows_rtmp_publish_url(windows_camera_stream)
    windows_camera_process = subprocess.Popen(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            windows_ffmpeg_command(ffmpeg_path, windows_camera_device, publish_url),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )
    return build_windows_camera_status()


@app.post("/api/windows-camera/stop", response_model=WindowsCameraStatus)
def stop_windows_camera():
    global windows_camera_process
    if windows_camera_process and windows_camera_process.poll() is None:
        windows_camera_process.terminate()
        try:
            windows_camera_process.wait(timeout=4)
        except subprocess.TimeoutExpired:
            windows_camera_process.kill()
    windows_camera_process = None
    return build_windows_camera_status()


@app.get("/api/live/{stream_name}.live.flv")
def proxy_flv_stream(stream_name: str):
    remote_url = f"{SRS_HTTP_URL}/live/{stream_name}.live.flv"
    response = open_remote(remote_url)

    def stream():
        try:
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                yield chunk
        finally:
            response.close()

    return StreamingResponse(stream(), media_type="video/x-flv")


@app.get("/api/streams/{stream_app}/{playlist_name}.m3u8")
def proxy_hls_playlist(stream_app: str, playlist_name: str, request: Request):
    remote_url = srs_url(f"/{stream_app}/{playlist_name}.m3u8", request.url.query)
    body = fetch_remote_bytes(remote_url).decode("utf-8", errors="replace")
    return Response(
        content=rewrite_hls_playlist(body, stream_app),
        media_type="application/vnd.apple.mpegurl",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/streams/{stream_app}/{segment_name}.ts")
def proxy_hls_segment(stream_app: str, segment_name: str, request: Request):
    remote_url = srs_url(f"/{stream_app}/{segment_name}.ts", request.url.query)
    response = open_remote(remote_url)

    def chunks():
        try:
            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                yield chunk
        finally:
            response.close()

    return StreamingResponse(chunks(), media_type="video/mp2t", headers={"Cache-Control": "no-store"})


@app.get("/api/streams/{stream_app}/{stream_name}.mjpeg")
def proxy_mjpeg_stream(stream_app: str, stream_name: str):
    if not shutil.which(FFMPEG_BIN):
        raise HTTPException(status_code=500, detail=f"ffmpeg not found: {FFMPEG_BIN}")

    source_url = f"rtmp://localhost/{stream_app}/{stream_name}"
    for cam in cameras.values():
        if cam.streamName == stream_name and cam.sourceUrl.startswith("rtsp://"):
            source_url = cam.sourceUrl
            break
    process = subprocess.Popen(
        [
            FFMPEG_BIN,
            "-hide_banner",
            "-loglevel",
            "error",
            "-fflags",
            "nobuffer",
            "-flags",
            "low_delay",
            "-i",
            source_url,
            "-an",
            "-vf",
            "fps=8,scale=960:-2",
            "-q:v",
            "6",
            "-f",
            "mjpeg",
            "pipe:1",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0,
    )

    def frames():
        buffer = b""
        try:
            while process.stdout:
                chunk = process.stdout.read(8192)
                if not chunk:
                    break
                buffer += chunk
                while True:
                    start = buffer.find(b"\xff\xd8")
                    end = buffer.find(b"\xff\xd9", start + 2)
                    if start < 0 or end < 0:
                        if start > 0:
                            buffer = buffer[start:]
                        break
                    frame = buffer[start : end + 2]
                    buffer = buffer[end + 2 :]
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        + f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii")
                        + frame
                        + b"\r\n"
                    )
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()

    return StreamingResponse(
        frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store"},
    )


def require_camera(camera_id: UUID) -> CameraResponse:
    camera = cameras.get(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera


def require_face(face_id: UUID) -> FaceProfileResponse:
    face = faces_store.get(face_id)
    if not face:
        raise HTTPException(status_code=404, detail="Face profile not found")
    return face


def require_deployment_task(task_id: UUID) -> DeploymentTaskResponse:
    task = deployment_tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Deployment task not found")
    return task


def require_model(model_name: str) -> ModelResponse:
    model = model_registry.get(model_name)
    if not model:
        raise HTTPException(status_code=404, detail="Model not registered")
    return model


def seed_model_registry() -> None:
    now = datetime.now(timezone.utc)
    defaults = [
        (
            UUID("00000000-0000-0000-0000-000000000101"),
            "scrfd_10g",
            "SCRFD-10GF",
            "FACE_DETECTION",
            "InsightFace SCRFD-10GF face detector and 5-point landmark model",
        ),
        (
            UUID("00000000-0000-0000-0000-000000000102"),
            "arcface_r50",
            "ArcFace R50",
            "FACE_RECOGNITION",
            "InsightFace ArcFace R50 face embedding model",
        ),
        (
            UUID("00000000-0000-0000-0000-000000000103"),
            "arcface_mbf",
            "ArcFace MobileFaceNet",
            "FACE_RECOGNITION",
            "InsightFace buffalo_s MobileFaceNet embedding model, w600k_mbf.onnx, about 13 MB",
        ),
    ]
    for model_id, name, display_name, model_type, description in defaults:
        if name in model_registry:
            continue
        model_registry[name] = ModelResponse(
            id=model_id,
            name=name,
            displayName=display_name,
            repositoryPath=f"/models/{name}",
            modelType=model_type,
            description=description,
            state="UNKNOWN",
            createdAt=now,
            updatedAt=now,
        )

    if TRITON_MODEL_REPOSITORY.is_dir():
        for path in sorted(TRITON_MODEL_REPOSITORY.iterdir()):
            if not path.is_dir() or path.name in model_registry:
                continue
            model_registry[path.name] = ModelResponse(
                id=uuid4(),
                name=path.name,
                displayName=path.name,
                repositoryPath=f"/models/{path.name}",
                modelType="OTHER",
                description=None,
                state="UNKNOWN",
                createdAt=now,
                updatedAt=now,
            )


def seed_cameras() -> None:
    if cameras:
        return
    now = datetime.now(timezone.utc)

    camera_entries = [
        ("NVR65-通道101", "rtsp://admin:cisdi123456@192.168.11.65:554/Streaming/Channels/101", "nvr65"),
        ("NVR198-通道101", "rtsp://admin:cisdi123@192.168.11.198:5504/Streaming/Channels/101", "nvr198"),
    ]
    for index in range(1, 21):
        camera_entries.append((
            f"摄像头{index:02d}",
            f"rtsp://192.168.11.195:8554/stream{index:02d}",
            f"cam{index:02d}",
        ))

    nvr65_streams = {0, 1}
    for idx, (name, source_url, stream_name) in enumerate(camera_entries):
        camera_id = uuid4()
        cameras[camera_id] = CameraResponse(
            id=camera_id,
            name=name,
            sourceUrl=source_url,
            streamApp="live",
            streamName=stream_name,
            description=None,
            area="办公楼",
            status="RUNNING",
            playbackUrl=playback_url(source_url, stream_name),
            createdAt=now,
            updatedAt=now,
            nvrId=None,
            nvrChannel=None,
            nvrTrackId=None,
            nvrStreamType=None,
        )
        add_zlmediakit_proxy(source_url, stream_name)
        if idx in nvr65_streams:
            try:
                start_worker_stream(cameras[camera_id])
            except Exception as exc:
                print(f"start_worker_stream failed for {stream_name}: {exc}", flush=True)


def seed_face_profiles() -> None:
    if faces_store:
        return
    src = PROJECT_ROOT / "R-C.jpg"
    if not src.is_file():
        print(f"seed: skip face profiles, R-C.jpg not found at {src}", flush=True)
        return
    face_id = uuid4()
    filename = f"{face_id}.jpg"
    dst = FACE_STORAGE_DIR / filename
    try:
        dst.write_bytes(src.read_bytes())
    except Exception as exc:
        print(f"seed: failed to copy {src} -> {dst}: {exc}", flush=True)
        return
    now = datetime.now(timezone.utc)
    face = FaceProfileResponse(
        id=face_id,
        name="测试人员-小美",
        description="项目根目录 R-C.jpg，用于布控任务测试",
        photoUrl=f"/api/assets/faces/{filename}",
        createdAt=now,
        updatedAt=now,
    )
    faces_store[face_id] = face
    persist_faces()
    print(f"seed: registered face profile 测试人员-小美 ({face_id})", flush=True)

def refresh_model_states() -> None:
    try:
        statuses = triton_request("/v2/repository/index", method="POST", payload={"ready": False})
    except HTTPException:
        return
    if not isinstance(statuses, list):
        return
    status_by_name = {
        item.get("name"): item
        for item in statuses
        if isinstance(item, dict) and item.get("name")
    }
    for name, status in status_by_name.items():
        if name not in model_registry:
            now = datetime.now(timezone.utc)
            model_registry[name] = ModelResponse(
                id=uuid4(),
                name=name,
                displayName=name,
                repositoryPath=f"/models/{name}",
                modelType="OTHER",
                description=status.get("reason"),
                state=str(status.get("state") or "UNKNOWN"),
                createdAt=now,
                updatedAt=now,
            )
            continue
        new_state = str(status.get("state") or "UNKNOWN")
        if model_registry[name].state != new_state:
            update_model_state(name, new_state)


def update_model_state(model_name: str, state: str) -> None:
    model = require_model(model_name)
    model_registry[model_name] = model.model_copy(
        update={
            "state": state,
            "updatedAt": datetime.now(timezone.utc),
        }
    )


def triton_request(path: str, method: str = "GET", payload: Optional[object] = None):
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = UrlRequest(f"{TRITON_HTTP_URL}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=8) as response:
            response_body = response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") or str(exc)
        raise HTTPException(status_code=502, detail=f"Triton request failed: {detail}") from exc
    except URLError as exc:
        raise HTTPException(status_code=502, detail=f"Triton is not reachable at {TRITON_HTTP_URL}: {exc.reason}") from exc
    if not response_body:
        return {}
    try:
        return json.loads(response_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Triton returned invalid JSON") from exc


async def save_face_photo(face_id: UUID, photo: UploadFile) -> str:
    if not photo.content_type or not photo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are supported")
    suffix = Path(photo.filename or "").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
        suffix = ".jpg"
    filename = f"{face_id}{suffix}"
    path = FACE_STORAGE_DIR / filename
    with path.open("wb") as output:
        while True:
            chunk = await photo.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
    return f"/api/assets/faces/{filename}"


def load_faces_from_disk() -> None:
    faces_store.clear()
    if FACE_METADATA_FILE.is_file():
        try:
            raw_faces = json.loads(FACE_METADATA_FILE.read_text(encoding="utf-8"))
            for raw in raw_faces:
                face = FaceProfileResponse(**raw)
                if asset_path(face.photoUrl, FACE_STORAGE_DIR) and asset_path(face.photoUrl, FACE_STORAGE_DIR).is_file():
                    faces_store[face.id] = face
        except Exception as exc:
            print(f"failed to load face metadata: {exc}", flush=True)
    recovered = False
    for path in sorted(FACE_STORAGE_DIR.iterdir()):
        if path.name in {".gitkeep", FACE_METADATA_FILE.name} or not path.is_file():
            continue
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
            continue
        try:
            face_id = UUID(path.stem)
        except ValueError:
            face_id = uuid4()
            new_path = path.with_name(f"{face_id}{path.suffix.lower()}")
            path.rename(new_path)
            path = new_path
        if face_id in faces_store:
            continue
        now = datetime.now(timezone.utc)
        faces_store[face_id] = FaceProfileResponse(
            id=face_id,
            name=f"未命名人脸-{str(face_id)[:8]}",
            description="从已保存照片恢复，请编辑姓名和描述",
            photoUrl=f"/api/assets/faces/{path.name}",
            createdAt=now,
            updatedAt=now,
        )
        recovered = True
    if recovered or (faces_store and not FACE_METADATA_FILE.is_file()):
        persist_faces()


def persist_faces() -> None:
    data = [json.loads(face.model_dump_json()) for face in sorted(faces_store.values(), key=lambda item: item.createdAt)]
    FACE_METADATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_face_embeddings() -> None:
    face_embeddings.clear()
    if FACE_EMBEDDINGS_FILE.is_file():
        try:
            raw = json.loads(FACE_EMBEDDINGS_FILE.read_text(encoding="utf-8"))
            for face_id, embedding in raw.items():
                try:
                    parsed_id = UUID(face_id)
                except ValueError:
                    continue
                if parsed_id in faces_store and isinstance(embedding, list):
                    face_embeddings[parsed_id] = [float(value) for value in embedding]
        except Exception as exc:
            print(f"failed to load face embeddings: {exc}", flush=True)
    changed = False
    for face in faces_store.values():
        if face.id not in face_embeddings:
            changed = refresh_face_embedding(face) or changed
    if changed:
        persist_face_embeddings()


def persist_face_embeddings() -> None:
    data = {str(face_id): embedding for face_id, embedding in face_embeddings.items() if face_id in faces_store}
    FACE_EMBEDDINGS_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def refresh_face_embedding(face: FaceProfileResponse) -> bool:
    path = asset_path(face.photoUrl, FACE_STORAGE_DIR)
    if path is None or not path.is_file():
        face_embeddings.pop(face.id, None)
        persist_face_embeddings()
        return False
    try:
        embedding = extract_face_embedding(path)
    except Exception as exc:
        face_embeddings.pop(face.id, None)
        persist_face_embeddings()
        print(f"failed to extract embedding for {face.name}: {exc}", flush=True)
        return False
    face_embeddings[face.id] = embedding
    persist_face_embeddings()
    return True


def extract_face_embedding(path: Path) -> List[float]:
    with path.open("rb") as photo:
        boundary = "----VideoAIBoundary"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
            "Content-Type: image/jpeg\r\n\r\n"
        ).encode("utf-8") + photo.read() + f"\r\n--{boundary}--\r\n".encode("utf-8")
    request = UrlRequest(
        f"{WORKER_URL}/v1/faces/extract",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") or str(exc)
        raise RuntimeError(f"worker extract failed: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"worker is not reachable at {WORKER_URL}: {exc.reason}") from exc
    embedding = payload.get("embedding")
    if not isinstance(embedding, list) or not embedding:
        raise RuntimeError("worker returned empty embedding")
    return [float(value) for value in embedding]


def delete_face_photo(photo_url: str) -> None:
    filename = photo_url.rsplit("/", 1)[-1]
    path = (FACE_STORAGE_DIR / filename).resolve()
    if str(path).startswith(str(FACE_STORAGE_DIR.resolve())) and path.is_file():
        path.unlink()


def cosine_similarity(left: List[float], right: List[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = 0.0
    left_norm = 0.0
    right_norm = 0.0
    for a, b in zip(left, right):
        dot += a * b
        left_norm += a * a
        right_norm += b * b
    denominator = math.sqrt(left_norm) * math.sqrt(right_norm)
    if denominator <= 0:
        return 0.0
    return dot / denominator


def start_worker_stream(camera: CameraResponse) -> None:
    payload = {
        "cameraId": str(camera.id),
        "cameraName": camera.name,
        "streamUrl": worker_stream_url(camera),
    }
    worker_request("/v1/streams/start", payload)


def stop_worker_stream(camera_id: UUID) -> None:
    worker_request("/v1/streams/stop", {"cameraId": str(camera_id)})


def worker_stream_url(camera: CameraResponse) -> str:
    if camera.sourceUrl.startswith("rtsp://"):
        return f"{SRS_HTTP_URL}/{camera.streamApp}/{camera.streamName}.live.flv"
    return camera.sourceUrl


def worker_request(path: str, payload: object) -> None:
    body = json.dumps(payload).encode("utf-8")
    request = UrlRequest(
        f"{WORKER_URL}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10):
            return
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") or str(exc)
        raise HTTPException(status_code=502, detail=f"Worker request failed: {detail}") from exc
    except URLError as exc:
        raise HTTPException(status_code=502, detail=f"Worker is not reachable at {WORKER_URL}: {exc.reason}") from exc


def add_zlmediakit_proxy(source_url: str, stream_name: str) -> None:
    if not source_url.startswith("rtsp://"):
        return
    proxy_url = f"{SRS_HTTP_URL}/index/api/addStreamProxy"
    params = f"secret={quote(ZLM_SECRET, safe='')}&vhost=__defaultVhost__&app=live&stream={quote(stream_name, safe='')}&url={quote(source_url, safe='')}&enable_rtsp=1&enable_rtmp=1&enable_hls=1&enable_fmp4=1"
    try:
        with urlopen(UrlRequest(f"{proxy_url}?{params}", method="GET"), timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        print(f"ZLM addStreamProxy failed for {stream_name}: {exc}", flush=True)
        return
    try:
        result = json.loads(body)
        if result.get("code") != 0:
            print(f"ZLM addStreamProxy error for {stream_name}: {body}", flush=True)
        else:
            print(f"ZLM addStreamProxy OK for {stream_name}", flush=True)
    except Exception:
        print(f"ZLM addStreamProxy unexpected response for {stream_name}: {body}", flush=True)


def remove_zlmediakit_proxy(stream_name: str) -> None:
    close_url = f"{SRS_HTTP_URL}/index/api/close_streams"
    params = f"secret={quote(ZLM_SECRET, safe='')}&vhost=__defaultVhost__&app=live&stream={quote(stream_name, safe='')}&force=1"
    try:
        with urlopen(UrlRequest(f"{close_url}?{params}", method="GET"), timeout=10) as resp:
            resp.read()
    except Exception:
        pass


def stream_proxy_guard_loop() -> None:
    """Periodically check ZLM for dead stream proxies and re-add them."""
    proxy_guard_stop_event.wait(30)
    while not proxy_guard_stop_event.is_set():
        try:
            active_streams = _fetch_active_streams()
            for camera in cameras.values():
                if camera.status != "RUNNING":
                    continue
                if camera.streamName not in active_streams:
                    print(f"stream_proxy_guard: re-adding proxy for {camera.streamName}", flush=True)
                    add_zlmediakit_proxy(camera.sourceUrl, camera.streamName)
        except Exception as exc:
            print(f"stream_proxy_guard failed: {exc}", flush=True)
        proxy_guard_stop_event.wait(30)


def _fetch_active_streams() -> set[str]:
    import json
    from urllib.request import urlopen
    api_url = f"{SRS_HTTP_URL}/index/api/getMediaList?secret={quote(ZLM_SECRET, safe='')}"
    try:
        with urlopen(api_url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("code") == 0:
            return {item.get("stream", "") for item in data.get("data", [])}
    except Exception:
        pass
    return set()


def face_scan_loop() -> None:
    if FACE_SCAN_INITIAL_DELAY_SECONDS > 0:
        scanner_stop_event.wait(FACE_SCAN_INITIAL_DELAY_SECONDS)
    while not scanner_stop_event.is_set():
        try:
            scan_running_cameras()
        except Exception as exc:
            print(f"face scan failed: {exc}", flush=True)
        scanner_stop_event.wait(max(FACE_SCAN_INTERVAL_SECONDS, 1))


def scan_running_cameras() -> FaceScanSummary:
    now = datetime.now(timezone.utc)
    running_cameras = [camera for camera in cameras.values() if camera.status == "RUNNING"]
    summary = FaceScanSummary(
        cameras=len(running_cameras),
        faces=len(faces_store),
        framesCaptured=0,
        faceDetections=0,
        matches=0,
        errors=[],
        scannedAt=now,
    )
    if not running_cameras or not faces_store:
        return summary

    for camera in running_cameras:
        try:
            if camera.streamName == "camera1" and "测试" in camera.name:
                continue
            frame = capture_camera_frame(camera)
            if not frame:
                summary.errors.append(f"{camera.name}: cannot capture frame")
                continue
            summary.framesCaptured += 1
            face_regions = detect_face_regions(frame)
            if not face_regions:
                continue
            summary.faceDetections += len(face_regions)
            for face_region in face_regions:
                face, similarity = match_face(face_region)
                if face is None:
                    continue
                event = create_face_event(
                    camera_id=camera.id,
                    face_profile_id=face.id,
                    camera_name=camera.name,
                    profile_name=face.name,
                    profile_description=face.description,
                    face_photo_url=face.photoUrl,
                    snapshot_base64=jpeg_data_url(frame),
                    video_time=now,
                    similarity=similarity,
                )
                if event is not None:
                    summary.matches += 1
        except Exception as exc:
            summary.errors.append(f"{camera.name}: {exc}")
    return summary


def capture_camera_frame(camera: CameraResponse) -> bytes:
    source_url = camera.sourceUrl
    if source_url.startswith("/api/streams/"):
        source_url = f"http://localhost:8081{source_url}"
    elif camera.playbackUrl.endswith(".mjpeg"):
        source_url = f"rtmp://localhost/{camera.streamApp}/{camera.streamName}"

    process = subprocess.run(
        [
            FFMPEG_BIN,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-rw_timeout",
            str(FACE_SCAN_TIMEOUT_SECONDS * 1_000_000),
            "-i",
            source_url,
            "-frames:v",
            "1",
            "-q:v",
            "3",
            "-f",
            "image2pipe",
            "-vcodec",
            "mjpeg",
            "pipe:1",
        ],
        capture_output=True,
        timeout=FACE_SCAN_TIMEOUT_SECONDS + 5,
    )
    if process.returncode != 0:
        return b""
    return process.stdout


def detect_face_regions(frame: bytes) -> List[bytes]:
    if not frame:
        return []
    script = """
import sys
try:
    import cv2
    import numpy as np
except Exception:
    sys.exit(2)
data = sys.stdin.buffer.read()
image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
if image is None:
    sys.exit(1)
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
variants = [
    gray,
    cv2.equalizeHist(gray),
    cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray),
]
cascade_names = [
    "haarcascade_frontalface_alt.xml",
    "haarcascade_frontalface_alt2.xml",
    "haarcascade_frontalface_default.xml",
]
boxes = []
height, width = gray.shape[:2]
min_size = max(40, min(width, height) // 14)
for cascade_name in cascade_names:
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + cascade_name)
    if cascade.empty():
        continue
    for variant in variants:
        for scale in (1.03, 1.05, 1.08, 1.1):
            faces = cascade.detectMultiScale(
                variant,
                scaleFactor=scale,
                minNeighbors=2,
                minSize=(min_size, min_size),
                flags=cv2.CASCADE_SCALE_IMAGE,
            )
            for x, y, w, h in faces:
                if w * h < min_size * min_size:
                    continue
                boxes.append((int(x), int(y), int(w), int(h)))
            if boxes:
                break
        if boxes:
            break
    if boxes:
        break

def iou(a, b):
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    ax2, ay2 = ax1 + aw, ay1 + ah
    bx2, by2 = bx1 + bw, by1 + bh
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    union = aw * ah + bw * bh - inter
    return inter / union if union else 0

merged = []
for box in sorted(boxes, key=lambda item: item[2] * item[3], reverse=True):
    if all(iou(box, kept) < 0.35 for kept in merged):
        merged.append(box)

sys.stdout.buffer.write(len(merged).to_bytes(2, "big"))
for x, y, w, h in merged[:5]:
    pad = int(max(w, h) * 0.25)
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(width, x + w + pad)
    y2 = min(height, y + h + pad)
    crop = image[y1:y2, x1:x2]
    ok, encoded = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not ok:
        sys.stdout.buffer.write((0).to_bytes(4, "big"))
        continue
    raw = encoded.tobytes()
    sys.stdout.buffer.write(len(raw).to_bytes(4, "big"))
    sys.stdout.buffer.write(raw)
"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            input=frame,
            capture_output=True,
            timeout=8,
        )
        if result.returncode == 2:
            return [frame]
        if result.returncode != 0 or len(result.stdout) < 2:
            return []
        count = int.from_bytes(result.stdout[:2], "big")
        offset = 2
        regions: List[bytes] = []
        for _ in range(count):
            if offset + 4 > len(result.stdout):
                break
            size = int.from_bytes(result.stdout[offset : offset + 4], "big")
            offset += 4
            if size <= 0 or offset + size > len(result.stdout):
                break
            regions.append(result.stdout[offset : offset + size])
            offset += size
        return regions
    except Exception:
        return [frame]


def match_face(face_region: bytes) -> tuple[Optional[FaceProfileResponse], float]:
    best_face: Optional[FaceProfileResponse] = None
    best_similarity = -1.0
    for face in faces_store.values():
        similarity = image_similarity(face_region, face.photoUrl)
        if similarity > best_similarity:
            best_similarity = similarity
            best_face = face
    if best_face is None:
        return None, 0.0
    if best_similarity < FACE_MATCH_THRESHOLD:
        return None, best_similarity
    return best_face, best_similarity


def image_similarity(frame: bytes, face_photo_url: str) -> float:
    face_path = asset_path(face_photo_url, FACE_STORAGE_DIR)
    if face_path is None or not face_path.is_file():
        return 0.0
    script = """
import sys
try:
    import cv2
    import numpy as np
except Exception:
    sys.exit(3)
frame_path, face_path = sys.argv[1], sys.argv[2]
frame = cv2.imread(frame_path, cv2.IMREAD_GRAYSCALE)
face = cv2.imread(face_path, cv2.IMREAD_GRAYSCALE)
if frame is None or face is None:
    sys.exit(2)
def hist(image):
    resized = cv2.resize(image, (128, 128))
    equalized = cv2.equalizeHist(resized)
    value = cv2.calcHist([equalized], [0], None, [64], [0, 256])
    cv2.normalize(value, value)
    return value
score = cv2.compareHist(hist(frame), hist(face), cv2.HISTCMP_CORREL)
print(max(0.0, min(1.0, (float(score) + 1.0) / 2.0)))
"""
    temp_path = SNAPSHOT_STORAGE_DIR / f"scan-{uuid4()}.jpg"
    try:
        temp_path.write_bytes(frame)
        result = subprocess.run(
            [sys.executable, "-c", script, str(temp_path), str(face_path)],
            capture_output=True,
            text=True,
            timeout=8,
        )
        if result.returncode == 3:
            return 1.0
        if result.returncode != 0:
            return 0.0
        return float(result.stdout.strip() or "0")
    except Exception:
        return 0.0
    finally:
        if temp_path.is_file():
            temp_path.unlink()


def create_face_event(
    camera_id: UUID,
    face_profile_id: UUID,
    camera_name: str,
    profile_name: str,
    profile_description: Optional[str],
    face_photo_url: str,
    snapshot_base64: Optional[str],
    video_time: datetime,
    similarity: float,
    deployment_task_id: Optional[UUID] = None,
) -> Optional[FaceEventResponse]:
    if recent_duplicate_event(camera_id, face_profile_id, deployment_task_id):
        return None
    now = datetime.now(timezone.utc)
    snapshot_url = save_snapshot(snapshot_base64)
    event = FaceEventResponse(
        id=uuid4(),
        cameraId=camera_id,
        faceProfileId=face_profile_id,
        cameraName=camera_name,
        profileName=profile_name,
        profileDescription=profile_description,
        facePhotoUrl=face_photo_url,
        snapshotUrl=snapshot_url,
        videoTime=video_time,
        similarity=max(0.0, min(1.0, similarity)),
        createdAt=now,
    )
    payload = f"event: face-event\ndata: {event.model_dump_json()}\n\n"
    with event_lock:
        events_store.insert(0, event)
        del events_store[200:]
        stale: List[queue.Queue[str]] = []
        for subscriber in event_subscribers:
            try:
                subscriber.put_nowait(payload)
            except queue.Full:
                stale.append(subscriber)
        for subscriber in stale:
            if subscriber in event_subscribers:
                event_subscribers.remove(subscriber)

    try:
        from db import SessionLocal
        from models import FaceMatchEventORM
        cam_obj = cameras.get(camera_id)
        camera_area = cam_obj.area if cam_obj else None
        with SessionLocal() as pgdb:
            row = FaceMatchEventORM(
                deployment_task_id=deployment_task_id,
                face_profile_id=face_profile_id,
                face_profile_name=profile_name,
                face_profile_photo_url=face_photo_url,
                snapshot_url=snapshot_url,
                camera_id=camera_id,
                camera_name=camera_name,
                camera_area=camera_area,
                similarity=max(0.0, min(1.0, similarity)),
                matched_at=video_time if isinstance(video_time, datetime) else now,
            )
            pgdb.add(row)
            pgdb.commit()
    except Exception as exc:
        print(f"FaceMatchEventORM insert failed: {exc}", flush=True)

    return event


def recent_duplicate_event(camera_id: UUID, profile_id: UUID, task_id: Optional[UUID] = None) -> bool:
    cutoff = time.time() - FACE_EVENT_COOLDOWN_SECONDS
    with event_lock:
        for event in events_store:
            if event.cameraId == camera_id and event.faceProfileId == profile_id and event.createdAt.timestamp() >= cutoff:
                return True
    if task_id is not None:
        try:
            from db import SessionLocal
            from models import FaceMatchEventORM
            from datetime import datetime, timezone
            with SessionLocal() as pgdb:
                recent = (
                    pgdb.query(FaceMatchEventORM)
                    .filter(
                        FaceMatchEventORM.camera_id == camera_id,
                        FaceMatchEventORM.face_profile_id == profile_id,
                        FaceMatchEventORM.deployment_task_id == task_id,
                    )
                    .order_by(FaceMatchEventORM.matched_at.desc())
                    .first()
                )
                if recent is not None and recent.matched_at is not None:
                    age = (datetime.now(timezone.utc) - recent.matched_at).total_seconds()
                    if age < FACE_EVENT_COOLDOWN_SECONDS:
                        return True
        except Exception:
            pass
    return False


def save_snapshot(snapshot_base64: Optional[str]) -> Optional[str]:
    if not snapshot_base64:
        return None
    data = snapshot_base64
    if "," in data:
        data = data.split(",", 1)[1]
    try:
        raw = base64.b64decode(data, validate=False)
    except Exception:
        return None
    if not raw:
        return None
    filename = f"{uuid4()}.jpg"
    (SNAPSHOT_STORAGE_DIR / filename).write_bytes(raw)
    return f"/api/assets/snapshots/{filename}"


def jpeg_data_url(frame: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(frame).decode("ascii")


def asset_path(asset_url: str, root: Path) -> Optional[Path]:
    if not asset_url:
        return None
    filename = asset_url.rsplit("/", 1)[-1]
    path = (root / filename).resolve()
    if not str(path).startswith(str(root.resolve())):
        return None
    return path


def stream_name_from_source(source_url: str) -> Optional[str]:
    marker = "/live/"
    if marker in source_url:
        return source_url.rsplit(marker, 1)[1].strip("/")
    return None


def playback_url(source_url: str, fallback_stream: str) -> str:
    stream_name = stream_name_from_source(source_url) or fallback_stream
    if source_url.startswith("rtsp://"):
        return f"/api/streams/live/{quote(stream_name, safe='')}.mjpeg"
    if stream_name and is_internal_stream_url(source_url):
        return f"/api/streams/live/{quote(stream_name, safe='')}.mjpeg"
    if source_url.startswith("http://") or source_url.startswith("https://"):
        return source_url
    return f"/api/streams/live/{quote(stream_name, safe='')}.mjpeg"


def is_internal_stream_url(source_url: str) -> bool:
    parsed = urlparse(source_url)
    return parsed.hostname in {"zlm", "host.docker.internal", "172.21.0.1", "localhost", "127.0.0.1"}


def clean_optional(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def srs_url(path: str, query: str = "") -> str:
    url = f"{SRS_HTTP_URL}/{path.lstrip('/')}"
    return f"{url}?{query}" if query else url


def open_remote(url: str):
    try:
        return urlopen(UrlRequest(url, headers={"User-Agent": "VideoAI-Lite/1.0"}), timeout=8)
    except HTTPError as error:
        raise HTTPException(status_code=error.code, detail=f"SRS stream request failed: {error.reason}") from error
    except URLError as error:
        raise HTTPException(status_code=502, detail=f"SRS stream unavailable: {error.reason}") from error


def fetch_remote_bytes(url: str) -> bytes:
    response = open_remote(url)
    try:
        return response.read()
    finally:
        response.close()


def rewrite_hls_playlist(playlist: str, stream_app: str) -> str:
    rewritten = []
    for raw_line in playlist.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            rewritten.append(raw_line)
            continue
        rewritten.append(rewrite_hls_uri(line, stream_app))
    if playlist.endswith("\n"):
        return "\n".join(rewritten) + "\n"
    return "\n".join(rewritten)


def rewrite_hls_uri(uri: str, stream_app: str) -> str:
    parsed = urlparse(uri)
    path = parsed.path
    query = parsed.query
    if path.startswith("/"):
        parts = path.strip("/").split("/", 1)
        app = parts[0] if parts else stream_app
        name = parts[1] if len(parts) > 1 else ""
    else:
        app = stream_app
        name = path
    rewritten = f"/api/streams/{quote(app, safe='')}/{quote(name, safe='')}"
    return f"{rewritten}?{query}" if query else rewritten


def build_windows_camera_status() -> WindowsCameraStatus:
    ffmpeg_path = find_windows_ffmpeg() if is_wsl_with_windows_tools() else None
    return WindowsCameraStatus(
        available=bool(ffmpeg_path),
        running=bool(windows_camera_process and windows_camera_process.poll() is None),
        ffmpegPath=ffmpeg_path,
        deviceName=windows_camera_device,
        streamName=windows_camera_stream,
        publishUrl=windows_rtmp_publish_url(windows_camera_stream),
        devices=list_windows_camera_devices(),
        message=None if ffmpeg_path else "Windows ffmpeg.exe not found. Run: winget install --id Gyan.FFmpeg -e",
    )


def is_wsl_with_windows_tools() -> bool:
    return shutil.which("powershell.exe") is not None


def find_windows_ffmpeg() -> Optional[str]:
    if not is_wsl_with_windows_tools():
        return None
    if "\\" in WINDOWS_FFMPEG_BIN or ":" in WINDOWS_FFMPEG_BIN:
        result = run_powershell(
            f"if (Test-Path {ps_quote(WINDOWS_FFMPEG_BIN)}) {{ Write-Output {ps_quote(WINDOWS_FFMPEG_BIN)} }}",
            timeout=5,
        )
        output = result.stdout.strip()
        if result.returncode == 0 and output:
            return output.splitlines()[0]
    command = (
        f"$cmd = Get-Command {ps_quote(WINDOWS_FFMPEG_BIN)} -ErrorAction SilentlyContinue; "
        "if ($cmd) { Write-Output $cmd.Source }"
    )
    result = run_powershell(command, timeout=5)
    if result.returncode != 0:
        return None
    output = result.stdout.strip()
    return output.splitlines()[0] if output else None


def list_windows_camera_devices() -> List[str]:
    if not is_wsl_with_windows_tools():
        return []
    command = (
        "Get-CimInstance Win32_PnPEntity | "
        "Where-Object { $_.PNPClass -eq 'Camera' -or $_.Name -match 'Camera|摄像|Webcam|USB Video|Integrated' } | "
        "Select-Object -ExpandProperty Name"
    )
    result = run_powershell(command, timeout=8)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def windows_rtmp_publish_url(stream_name: str) -> str:
    return f"rtmp://{local_wsl_ip()}/live/{stream_name}"


def local_wsl_ip() -> str:
    result = subprocess.run(["hostname", "-I"], capture_output=True, text=True, timeout=3)
    return result.stdout.split()[0] if result.stdout.split() else "127.0.0.1"


def windows_ffmpeg_command(ffmpeg_path: str, device_name: str, publish_url: str) -> str:
    return (
        f"& {ps_quote(ffmpeg_path)} "
        "-hide_banner -loglevel warning -f dshow "
        f"-rtbufsize 256M -framerate 25 -video_size 1280x720 -i {ps_quote('video=' + device_name)} "
        "-an -c:v libx264 -preset veryfast -tune zerolatency -profile:v baseline "
        "-pix_fmt yuv420p -g 25 -keyint_min 25 -sc_threshold 0 "
        f"-f flv {ps_quote(publish_url)}"
    )


def ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="frontend_assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        index_path = FRONTEND_DIST / "index.html"
        if index_path.is_file():
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="Frontend not built")


def run_powershell(command: str, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
