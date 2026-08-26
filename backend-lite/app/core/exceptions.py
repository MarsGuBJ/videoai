"""统一应用异常层级与错误码。

对外 HTTP 契约仍以 FastAPI HTTPException 的 {"detail": ...} 结构为准；
AppError 用于服务层内部错误，经全局 handler 转为 {code, message, traceId}
（仅新增字段，不影响既有契约）。
"""


class ErrorCode:
    """集中错误码，命名规则：模块_编号。"""

    FACE_001 = "FACE_001"
    EVENT_001 = "EVENT_001"
    TASK_001 = "TASK_001"
    MODEL_001 = "MODEL_001"
    SEARCH_001 = "SEARCH_001"
    CAMERA_001 = "CAMERA_001"
    INTERNAL_001 = "INTERNAL_001"


class AppError(Exception):
    """应用异常基类。

    Args:
        message: 面向调用方的错误描述。
        code: 错误码，默认取子类类属性。
        status_code: HTTP 状态码，默认 400。
    """

    code: str = ErrorCode.INTERNAL_001
    status_code: int = 400

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code


class FaceError(AppError):
    code = ErrorCode.FACE_001


class EventError(AppError):
    code = ErrorCode.EVENT_001


class TaskError(AppError):
    code = ErrorCode.TASK_001


class ModelError(AppError):
    code = ErrorCode.MODEL_001


class SearchError(AppError):
    code = ErrorCode.SEARCH_001


class CameraError(AppError):
    code = ErrorCode.CAMERA_001


class InternalError(AppError):
    code = ErrorCode.INTERNAL_001
    status_code = 500
