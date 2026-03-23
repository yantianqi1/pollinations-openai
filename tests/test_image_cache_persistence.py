import tempfile
import unittest
from pathlib import Path

from app.services.image_cache import ImageCache


class ImageCachePersistenceTest(unittest.TestCase):
    def test_store_persists_image_for_new_cache_instances(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir)
            first_cache = ImageCache(storage_dir=storage_dir)
            image_id = first_cache.store(b"image-bytes", "image/png")

            second_cache = ImageCache(storage_dir=storage_dir)

            self.assertEqual(
                second_cache.get(image_id),
                (b"image-bytes", "image/png"),
            )
