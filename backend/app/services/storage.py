"""Storage adapter — abstracts file storage behind a simple interface.

Supports local filesystem (default) and S3-compatible storage.
Switch by setting STORAGE_BACKEND=s3 + S3 credentials in env.

Usage:
    from app.services.storage import storage

    # Save a file
    path = await storage.save(tenant_id, filename, content, content_type)

    # Read a file
    data = await storage.read(path)

    # Delete a file
    await storage.delete(path)

    # Get a local path for serving (local only, S3 returns None)
    local = storage.get_local_path(path)
"""

import os
import uuid
from typing import Protocol

from app.core.config import settings


class StorageBackend(Protocol):
    async def save(self, tenant_id: uuid.UUID, filename: str, content: bytes, content_type: str) -> str: ...
    async def read(self, path: str) -> bytes: ...
    async def delete(self, path: str) -> None: ...
    def get_local_path(self, path: str) -> str | None: ...


class LocalStorage:
    """Store files on the local filesystem (Docker volume)."""

    def __init__(self, root: str = "/app/uploads"):
        self.root = root

    async def save(self, tenant_id: uuid.UUID, filename: str, content: bytes, content_type: str) -> str:
        tenant_dir = os.path.join(self.root, str(tenant_id))
        os.makedirs(tenant_dir, exist_ok=True)
        safe_name = f"{uuid.uuid4()}_{filename}"
        path = os.path.join(tenant_dir, safe_name)
        with open(path, "wb") as f:
            f.write(content)
        return path

    async def read(self, path: str) -> bytes:
        with open(path, "rb") as f:
            return f.read()

    async def delete(self, path: str) -> None:
        if os.path.exists(path):
            os.remove(path)

    def get_local_path(self, path: str) -> str | None:
        return path if os.path.exists(path) else None


class S3Storage:
    """Store files in S3-compatible storage (AWS S3, MinIO, DigitalOcean Spaces)."""

    def __init__(self):
        try:
            import boto3
            self.s3 = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT_URL or None,
                aws_access_key_id=settings.S3_ACCESS_KEY_ID or "",
                aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY or "",
                region_name=settings.S3_REGION or "us-east-1",
            )
            self.bucket = settings.S3_BUCKET or "bluewave-assets"
            self.public_url = settings.S3_PUBLIC_URL
        except ImportError:
            raise RuntimeError("boto3 is required for S3 storage. Install with: pip install boto3")

    def _key(self, tenant_id: uuid.UUID, filename: str) -> str:
        return f"{tenant_id}/{uuid.uuid4()}_{filename}"

    async def save(self, tenant_id: uuid.UUID, filename: str, content: bytes, content_type: str) -> str:
        import asyncio
        key = self._key(tenant_id, filename)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.s3.put_object(
                Bucket=self.bucket, Key=key, Body=content, ContentType=content_type
            ),
        )
        return f"s3://{self.bucket}/{key}"

    async def read(self, path: str) -> bytes:
        import asyncio
        _, _, key = path.replace("s3://", "").partition("/")
        loop = asyncio.get_event_loop()
        obj = await loop.run_in_executor(
            None,
            lambda: self.s3.get_object(Bucket=self.bucket, Key=key),
        )
        return obj["Body"].read()

    async def delete(self, path: str) -> None:
        import asyncio
        _, _, key = path.replace("s3://", "").partition("/")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.s3.delete_object(Bucket=self.bucket, Key=key),
        )

    def get_local_path(self, path: str) -> str | None:
        return None  # S3 files aren't local


def _create_storage() -> StorageBackend:
    backend = settings.STORAGE_BACKEND.lower()
    if backend == "s3":
        return S3Storage()
    return LocalStorage()


storage: StorageBackend = _create_storage()
