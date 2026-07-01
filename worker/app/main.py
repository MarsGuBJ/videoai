import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile

from .config import settings
from .schemas import EmbeddingResponse, StreamStartRequest, StreamStatusResponse, StreamStopRequest
from .stream_manager import StreamManager
from .triton_models import TritonFaceClient

app = FastAPI(title="VideoAI Worker", version="0.1.0")
settings_value = settings()
face_client = TritonFaceClient(settings_value)
stream_manager = StreamManager(settings_value, face_client)


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

