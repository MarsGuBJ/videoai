"""布控任务 DTO。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

DEFAULT_RECOGNITION_PER_MINUTE = 60
DEFAULT_SIMILARITY = 50

# 必填的日期/时间格式：与前端 date / time 输入框的输出一致
DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"
TIME_PATTERN = r"^\d{2}:\d{2}$"


def check_real_date(value: str | None) -> str | None:
    """日期需为真实存在的 YYYY-MM-DD（挡掉 2026-13-45 这类值）。"""
    if value is None:
        return None
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("日期必须是 YYYY-MM-DD 且真实存在") from exc
    return value


def check_real_time(value: str | None) -> str | None:
    """时间需为 24 小时制的 HH:MM（挡掉 25:00 这类值；正则只保证两位数字）。"""
    if value is None:
        return None
    if int(value[:2]) > 23 or int(value[3:]) > 59:
        raise ValueError("时间必须是 24 小时制的 HH:MM")
    return value


class DeploymentTaskResponse(BaseModel):
    id: UUID
    name: str
    pipeline: str
    area: str
    areaCount: int
    enabled: bool
    taskStatus: str
    desc: str
    faceProfileId: UUID | None = None
    faceProfileName: str | None = None
    faceProfilePhotoUrl: str | None = None
    cameraIds: list[str]
    recognitionPerMinute: int = Field(default=DEFAULT_RECOGNITION_PER_MINUTE, ge=1)
    similarity: int = Field(default=DEFAULT_SIMILARITY, ge=0, le=100)
    effectiveStart: str | None = None
    effectiveEnd: str | None = None
    cycleStart: str | None = None
    cycleEnd: str | None = None
    algorithmId: UUID | None = None
    algorithmName: str | None = None
    engineType: str | None = None
    algorithmCode: str | None = None
    createdAt: datetime
    updatedAt: datetime


class DeploymentTaskCreateRequest(BaseModel):
    """创建布控任务：必填项与「新建布控任务」弹窗 / 「快速布防」页的标星字段一一对应。

    布控目标图、事件编号、监控点位、生效时间、循环周期、相似度缺一不可——历史上这些字段都是
    可选的，调用方漏传就会建出"图片和属性不全"的半成品任务（后端拿默认值兜底，界面上看不出问题）。
    """

    name: str = Field(min_length=1, max_length=200)
    pipeline: str = "人脸识别流程"
    area: str | None = None
    areaCount: int = 0
    enabled: bool = True
    desc: str = ""
    faceProfileId: UUID | None = None
    faceProfileName: str | None = None
    # 布控目标图（本地/框选/人脸库选取后的可访问地址）
    faceProfilePhotoUrl: str = Field(min_length=1, max_length=1000)
    cameraIds: list[str] = Field(min_length=1)
    recognitionPerMinute: int = Field(default=DEFAULT_RECOGNITION_PER_MINUTE, ge=1)
    similarity: int = Field(ge=0, le=100)
    effectiveStart: str = Field(pattern=DATE_PATTERN)
    effectiveEnd: str = Field(pattern=DATE_PATTERN)
    cycleStart: str = Field(pattern=TIME_PATTERN)
    cycleEnd: str = Field(pattern=TIME_PATTERN)
    algorithmId: UUID | None = None
    algorithmCode: str = Field(min_length=1, max_length=100)

    @field_validator(
        "name",
        "faceProfilePhotoUrl",
        "algorithmCode",
        "effectiveStart",
        "effectiveEnd",
        "cycleStart",
        "cycleEnd",
        mode="before",
    )
    @classmethod
    def _strip_required_text(cls, value: object) -> object:
        """必填文本先去掉首尾空白，避免只填空格绕过 min_length。"""
        return value.strip() if isinstance(value, str) else value

    @field_validator("effectiveStart", "effectiveEnd")
    @classmethod
    def _check_dates(cls, value: str) -> str:
        return check_real_date(value) or value

    @field_validator("cycleStart", "cycleEnd")
    @classmethod
    def _check_times(cls, value: str) -> str:
        return check_real_time(value) or value


class DeploymentTaskUpdateRequest(BaseModel):
    """部分更新：字段可选（缺省=不改），但显式传入时仍要满足约束，避免把必填项改空。"""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    pipeline: str | None = None
    area: str | None = None
    areaCount: int | None = None
    enabled: bool | None = None
    taskStatus: str | None = None
    desc: str | None = None
    faceProfileId: UUID | None = None
    faceProfileName: str | None = None
    faceProfilePhotoUrl: str | None = Field(default=None, min_length=1, max_length=1000)
    cameraIds: list[str] | None = Field(default=None, min_length=1)
    recognitionPerMinute: int | None = Field(default=None, ge=1)
    similarity: int | None = Field(default=None, ge=0, le=100)
    effectiveStart: str | None = Field(default=None, pattern=DATE_PATTERN)
    effectiveEnd: str | None = Field(default=None, pattern=DATE_PATTERN)
    cycleStart: str | None = Field(default=None, pattern=TIME_PATTERN)
    cycleEnd: str | None = Field(default=None, pattern=TIME_PATTERN)
    algorithmId: UUID | None = None
    algorithmCode: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("effectiveStart", "effectiveEnd")
    @classmethod
    def _check_dates(cls, value: str | None) -> str | None:
        return check_real_date(value)

    @field_validator("cycleStart", "cycleEnd")
    @classmethod
    def _check_times(cls, value: str | None) -> str | None:
        return check_real_time(value)
