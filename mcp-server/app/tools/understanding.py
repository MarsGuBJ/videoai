"""Video understanding MCP tool."""

from ..context import mcp, video_understanding_client


@mcp.tool()
async def video_understanding(
    videoUrl: str = "",
    question: str = "",
    fps: int = 1,
    segmentSeconds: int = 60,
    maxSegments: int = 0,
    height: int = 480,
    prompt: str = "",
) -> dict:
    """Analyze an MP4 video URL (e.g. a MinIO object) and return structured events: the
    upstream service runs video understanding, then uses DeepSeek to organize the result
    into events (name, time range, description, relevance to the question), extracts a key
    frame per event, and picks the focus event that answers `question`. The video is sampled
    at fps frames per second and split into segmentSeconds-long segments; maxSegments=0
    analyzes all segments. Returns the upstream response (code/message/data; data contains
    summary, answer_status, focus_event, events and raw_understanding_result)."""
    return await video_understanding_client.structure(
        videoUrl, question, fps, segmentSeconds, maxSegments, height, prompt
    )
