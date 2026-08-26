"""Face library MCP tools."""

from ..context import mcp, videoai


@mcp.tool()
async def upload_face_image(imageUrl: str, cameraId: str, modelName: str, name: str = "人脸库照片") -> dict:
    """Upload a face image URL, create an enabled face deployment task for cameraId, and return both records.
    The task is visible on the deployment task page and starts in running status."""
    face_result = await videoai.upload_face(imageUrl, cameraId, modelName, name)
    face_id = str(face_result.get("faceId") or face_result.get("id") or "").strip()
    if not face_id:
        raise ValueError("face upload response did not include faceId")

    face_profile = await videoai.get_face(face_id)
    task_payload = {
        "name": name or face_profile.get("name") or "人脸识别布控",
        "pipeline": modelName or "人脸识别流程",
        "area": "默认区域",
        "areaCount": 1,
        "enabled": True,
        "desc": "MCP upload_face_image 自动创建",
        "faceProfileId": face_id,
        "faceProfileName": face_profile.get("name") or name,
        "faceProfilePhotoUrl": face_profile.get("photoUrl"),
        "cameraIds": [cameraId],
    }
    deployment_task = await videoai.create_deployment_task(task_payload)
    return {
        "faceId": face_id,
        "face": face_profile,
        "deploymentTaskId": deployment_task.get("id"),
        "deploymentTask": deployment_task,
    }


@mcp.tool()
async def query_face_matches(faceId: str = "", limit: int = 10) -> dict:
    """Query face match events identified by the face library.
    If faceId is provided, returns matching events for that specific face.
    If faceId is empty, returns the latest match events across all faces (max 10).
    Results are sorted by video time descending."""
    matches = await videoai.query_face_matches(faceId if faceId else None, limit)
    return {"data": matches, "count": len(matches)}
