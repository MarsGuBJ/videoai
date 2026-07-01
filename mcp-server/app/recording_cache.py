from datetime import datetime, timedelta, timezone

from .models import RecordingSegment


class RecordingCache:
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, tuple[datetime, RecordingSegment]] = {}

    def put_many(self, recordings: list[RecordingSegment]) -> None:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.ttl_seconds)
        for recording in recordings:
            self._items[recording.recordingId] = (expires_at, recording)

    def get(self, recording_id: str) -> RecordingSegment | None:
        item = self._items.get(recording_id)
        if item is None:
            return None
        expires_at, recording = item
        if expires_at <= datetime.now(timezone.utc):
            self._items.pop(recording_id, None)
            return None
        return recording
