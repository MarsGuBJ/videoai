from __future__ import annotations

from pathlib import Path


class RecordingMp4Storage:
    def __init__(
        self,
        endpoint: str,
        port: int,
        use_ssl: bool,
        access_key: str,
        secret_key: str,
        bucket: str,
    ) -> None:
        self.endpoint = endpoint.strip()
        self.port = port
        self.use_ssl = use_ssl
        self.bucket = bucket.strip()
        self.access_key = access_key
        self.secret_key = secret_key
        self._client = None

    def upload_mp4(self, source_file: Path, object_name: str) -> str:
        client = self._get_client()
        if not client.bucket_exists(self.bucket):
            client.make_bucket(self.bucket)
        client.fput_object(
            self.bucket,
            object_name,
            str(source_file),
            content_type="video/mp4",
        )
        scheme = "https" if self.use_ssl else "http"
        return f"{scheme}://{self.endpoint}:{self.port}/{self.bucket}/{object_name}"

    def _get_client(self):
        if self._client is None:
            # 保持惰性导入：仅在容器内使用，本地/测试环境不要求安装 minio
            from minio import Minio

            self._client = Minio(
                f"{self.endpoint}:{self.port}",
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.use_ssl,
            )
        return self._client
