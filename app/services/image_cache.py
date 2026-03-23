import asyncio
import sys
import time
import uuid
from collections import OrderedDict
from typing import Dict, Optional, Tuple

from app.config import settings


class ImageCache:
    def __init__(self) -> None:
        self._cache: OrderedDict[str, Tuple[bytes, str, float]] = OrderedDict()
        self._cleanup_task: Optional[asyncio.Task] = None

    def store(self, image_bytes: bytes, content_type: str = "image/jpeg") -> str:
        image_id = uuid.uuid4().hex
        now = time.time()

        # Evict oldest entries if at capacity
        while len(self._cache) >= settings.image_cache_max_size:
            self._cache.popitem(last=False)

        self._cache[image_id] = (image_bytes, content_type, now)
        return image_id

    def get(self, image_id: str) -> Optional[Tuple[bytes, str]]:
        entry = self._cache.get(image_id)
        if entry is None:
            return None
        image_bytes, content_type, timestamp = entry
        if time.time() - timestamp > settings.image_cache_ttl:
            del self._cache[image_id]
            return None
        return image_bytes, content_type

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired = [
            k for k, (_, _, ts) in self._cache.items()
            if now - ts > settings.image_cache_ttl
        ]
        for k in expired:
            del self._cache[k]

    def stats(self) -> Dict[str, object]:
        memory_bytes = sum(sys.getsizeof(b) for b, _, _ in self._cache.values())
        return {
            "cache_count": len(self._cache),
            "cache_max": settings.image_cache_max_size,
            "cache_memory_mb": round(memory_bytes / 1024 / 1024, 2),
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
