import time
import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import StreamingResponse
from uuid import UUID

from .config import settings
from .schemas import EmbeddingResponse, StreamStartRequest, StreamStatusResponse, StreamStopRequest
from .stream_manager import StreamManager
from .triton_models import DinoDetectionClient, TritonFaceClient

app = FastAPI(title="VideoAI Worker", version="0.1.0")
settings_value = settings()
face_client = TritonFaceClient(settings_value)
dino_client = DinoDetectionClient(settings_value) if settings_value.object_detection_enabled else None
stream_manager = StreamManager(settings_value, face_client, dino_client)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/faces/extract", response_model=EmbeddingResponse)
async def extract_face(file: UploadFile = File(...)):
    data = await file.read()
    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="invalid image")
    embedding = face_client.extract_embedding(image)
    return EmbeddingResponse(embedding=embedding)


@app.post("/v1/streams/start")
def start_stream(request: StreamStartRequest):
    stream_manager.start(request)
    return {"status": "started"}


@app.post("/v1/streams/stop")
def stop_stream(request: StreamStopRequest):
    stream_manager.stop(request.cameraId)
    return {"status": "stopped"}


@app.get("/v1/streams", response_model=StreamStatusResponse)
def streams():
    return StreamStatusResponse(streams=stream_manager.status())


@app.get("/v1/streams/annotated.mjpeg")
async def annotated_mjpeg(cameraId: UUID = Query(...)):
    def generate():
        while True:
            frame = stream_manager.get_annotated_frame(str(cameraId))
            if frame is not None:
                ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if ok:
                    yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + encoded.tobytes() + b"\r\n")
            time.sleep(0.5)
    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")

