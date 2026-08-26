"""兼容壳：ORM 模型已拆至 app/models/，此处仅 re-export。

CameraORM 为无引用死代码，已在重构中删除（全仓 grep 确认仅定义处出现）。
"""

from app.models.deployment_task import DeploymentTaskORM
from app.models.face_match_event import FaceMatchEventORM

__all__ = ["DeploymentTaskORM", "FaceMatchEventORM"]
