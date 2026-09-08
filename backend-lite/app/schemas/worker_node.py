"""Worker 节点资源监控 DTO（对外契约 camelCase）。"""

from datetime import datetime

from pydantic import BaseModel, Field


class GpuMetricIn(BaseModel):
    """worker 心跳上报的单卡 GPU 指标。"""

    index: int
    name: str
    memoryTotalMb: int
    memoryUsedMb: int
    temperatureC: int
    powerW: float
    utilizationPct: int


class SystemMetricIn(BaseModel):
    """worker 心跳上报的宿主机系统指标（CPU/内存/磁盘）。"""

    cpuPercent: float = 0.0
    memoryTotalMb: int = 0
    memoryUsedMb: int = 0
    diskTotalGb: float = 0.0
    diskUsedGb: float = 0.0


class WorkerHeartbeatIn(BaseModel):
    """worker → backend-lite 心跳请求体。"""

    hostname: str = Field(min_length=1)
    ip: str = ""
    port: int = 0
    gpus: list[GpuMetricIn] = []
    # 旧版 worker 不上报系统指标，默认全零
    system: SystemMetricIn = Field(default_factory=SystemMetricIn)


class GpuOut(GpuMetricIn):
    """对外返回的单卡 GPU 指标（含派生状态：繁忙 / 空闲 / 离线）。"""

    status: str


class WorkerNodeOut(BaseModel):
    """对外返回的 worker 节点（id = hostname）。"""

    id: str
    hostname: str
    ip: str
    port: int
    status: str  # 在线 / 离线
    lastSeenAt: datetime
    gpus: list[GpuOut]
    system: SystemMetricIn = Field(default_factory=SystemMetricIn)
    createdAt: datetime
    updatedAt: datetime
