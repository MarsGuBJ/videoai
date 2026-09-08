"""MinIO video analysis MCP tool."""

from ..context import mcp, video_analysis


@mcp.tool()
async def analyze_minio_video(
    videoUrl: str = "",
    prompt: str = "",
    fps: int = 1,
    segmentSeconds: int = 60,
    maxSegments: int = 1,
    height: int = 480,
) -> dict:
    """Analyze a video file URL (e.g. a MinIO MP4) with a custom prompt through the video
    analysis service. The video is sampled at fps frames per second and split into
    segmentSeconds-long segments; at most maxSegments segments are analyzed. Returns the
    analysis service response (code/segments/summary fields)."""
    return await video_analysis.analyze_minio_video(videoUrl, prompt, fps, segmentSeconds, maxSegments, height)
