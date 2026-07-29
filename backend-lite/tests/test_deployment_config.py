from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_backend_compose_injects_on_demand_preview_settings():
    compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "VIDEOAI_PREVIEW_IDLE_SECONDS:" in compose
    assert "VIDEOAI_PREVIEW_START_TIMEOUT_MS:" in compose
    assert "VIDEOAI_PREVIEW_FFMPEG_CMD_KEY:" in compose
    assert "VIDEOAI_ZLM_PREVIEW_RTMP_BASE:" in compose
    assert "UVICORN_WORKERS: ${UVICORN_WORKERS:-1}" in compose


def test_example_environment_documents_non_secret_preview_defaults():
    env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")

    assert "VIDEOAI_PREVIEW_IDLE_SECONDS=60" in env_example
    assert "VIDEOAI_PREVIEW_START_TIMEOUT_MS=15000" in env_example
    assert "VIDEOAI_PREVIEW_FFMPEG_CMD_KEY=ffmpeg.cmd_preview_h264" in env_example
    assert "ZLM_PREVIEW_RTMP_BASE=rtmp://127.0.0.1/live" in env_example


def test_backend_image_contains_preview_relay_module():
    dockerfile = (PROJECT_ROOT / "backend-lite" / "Dockerfile").read_text(encoding="utf-8")

    assert "COPY preview_relay.py ." in dockerfile
    assert "ENV UVICORN_WORKERS=1" in dockerfile
    assert "${UVICORN_WORKERS:-1}" in dockerfile
