import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

from app.config import settings

IMAGE_FILE_SUFFIX = ".bin"
METADATA_FILE_SUFFIX = ".json"


@dataclass(frozen=True)
class ImageRecord:
    image_id: str
    image_path: Path
    metadata_path: Path
    content_type: str
    timestamp: float


class ImageCache:
    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        self._cleanup_task: Optional[asyncio.Task] = None
        self._storage_dir = storage_dir or Path(settings.image_storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def store(self, image_bytes: bytes, content_type: str = "image/jpeg") -> str:
        image_id = uuid.uuid4().hex
        now = time.time()
        self._prune_to_capacity()
        image_path, metadata_path = self._paths_for(image_id)
        image_path.write_bytes(image_bytes)
        metadata = {"content_type": content_type, "timestamp": now}
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
        return image_id

    def get(self, image_id: str) -> Optional[Tuple[bytes, str]]:
        record = self._load_record(image_id)
        if record is None:
            return None
        if self._is_expired(record.timestamp):
            self._delete_record(record)
            return None
        return record.image_path.read_bytes(), record.content_type

    def _paths_for(self, image_id: str) -> Tuple[Path, Path]:
        image_path = self._storage_dir / f"{image_id}{IMAGE_FILE_SUFFIX}"
        metadata_path = self._storage_dir / f"{image_id}{METADATA_FILE_SUFFIX}"
        return image_path, metadata_path

    def _load_record(self, image_id: str) -> Optional[ImageRecord]:
        image_path, metadata_path = self._paths_for(image_id)
        if not image_path.exists() or not metadata_path.exists():
            return None
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        content_type = metadata.get("content_type")
        timestamp = metadata.get("timestamp")
        if not isinstance(content_type, str) or not isinstance(timestamp, (int, float)):
            return None
        return ImageRecord(
            image_id=image_id,
            image_path=image_path,
            metadata_path=metadata_path,
            content_type=content_type,
            timestamp=float(timestamp),
        )

    def _list_records(self) -> list[ImageRecord]:
        image_ids = [path.stem for path in self._storage_dir.glob(f"*{METADATA_FILE_SUFFIX}")]
        return [
            record
            for image_id in image_ids
            if (record := self._load_record(image_id)) is not None
        ]

    def _is_expired(self, timestamp: float) -> bool:
        return time.time() - timestamp > settings.image_cache_ttl

    def _cleanup_expired(self) -> None:
        for record in self._list_records():
            if self._is_expired(record.timestamp):
                self._delete_record(record)

    def _delete_record(self, record: ImageRecord) -> None:
        for path in (record.image_path, record.metadata_path):
            try:
                path.unlink()
            except FileNotFoundError:
                continue

    def _prune_to_capacity(self) -> None:
        records = self._list_records()
        while len(records) >= settings.image_cache_max_size:
            oldest = min(records, key=lambda record: record.timestamp)
            self._delete_record(oldest)
            records = [
                record for record in records if record.image_id != oldest.image_id
            ]

    def stats(self) -> Dict[str, object]:
        records = self._list_records()
        storage_bytes = sum(record.image_path.stat().st_size for record in records)
        return {
            "cache_count": len(records),
            "cache_max": settings.image_cache_max_size,
            "cache_memory_mb": round(storage_bytes / 1024 / 1024, 2),
        }

    async def start_cleanup_loop(self) -> None:
        async def _loop() -> None:
            while True:
                await asyncio.sleep(60)
                self._cleanup_expired()

        self._cleanup_task = asyncio.create_task(_loop())

    async def stop_cleanup_loop(self) -> None:
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass


image_cache = ImageCache()
