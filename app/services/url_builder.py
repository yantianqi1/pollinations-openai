import random
from typing import Optional, Tuple
from urllib.parse import quote

from app.config import settings


def parse_size(size: str) -> Tuple[int, int]:
    parts = size.lower().split("x")
    if len(parts) != 2:
        return 1024, 1024
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return 1024, 1024


def build_pollinations_image_url(
    prompt: str,
    model: str,
    width: int = 1024,
    height: int = 1024,
    seed: Optional[int] = None,
) -> str:
    if seed is None:
        seed = random.randint(0, 2**31)

    encoded_prompt = quote(prompt, safe="")
    base = settings.pollinations_base_url.rstrip("/")

    params = {
        "model": model,
        "width": str(width),
        "height": str(height),
        "seed": str(seed),
        "nologo": str(settings.default_nologo).lower(),
        "private": str(settings.default_private).lower(),
    }

    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{base}/{encoded_prompt}?{query}"
