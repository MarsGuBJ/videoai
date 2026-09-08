"""兼容壳：ORM 模型已拆至 app/models/，此处仅 re-export。

CameraORM 为无引用死代码，已在重构中删除（全仓 grep 确认仅定义处出现）。
FaceMatchEventORM 已退役，统一由 DeploymentEventORM（deployment_events 表）取代。
"""

from app.models.deployment_event import DeploymentEventORM
from app.models.deployment_task import DeploymentTaskORM

__all__ = ["DeploymentEventORM", "DeploymentTaskORM"]
