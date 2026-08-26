"""ORM 模型包。"""

from app.models.deployment_task import DeploymentTaskORM
from app.models.face_match_event import FaceMatchEventORM

__all__ = ["DeploymentTaskORM", "FaceMatchEventORM"]
