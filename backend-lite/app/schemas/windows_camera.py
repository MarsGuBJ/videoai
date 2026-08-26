"""Windows 摄像头（WSL 推流）DTO。"""

from pydantic import BaseModel


class WindowsCameraStartRequest(BaseModel):
    deviceName: str | None = None
    streamName: str | None = None


class WindowsCameraStatus(BaseModel):
    available: bool
    running: bool
    ffmpegPath: str | None = None
    deviceName: str
    streamName: str
    publishUrl: str
    devices: list[str]
    message: str | None = None
