import os
import hashlib
import time
from typing import Optional, Dict

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "preview_cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def _make_cache_path(key: str) -> str:
    # Use hash to avoid unsafe filenames
    hashed = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return os.path.join(CACHE_DIR, f"{hashed}.png")


class PreviewCache:
    """
    Disk-based cache for shape previews (PNG images).
    """

    def __init__(self, expiry_seconds: int = 3600):
        self.cache_dir = CACHE_DIR
        self.expiry = expiry_seconds

    def get_cached_preview(self, key: str, cache_expiry: Optional[int] = None) -> Optional[bytes]:
        """Return PNG data if cache file is present and fresh, else None."""
        cache_expiry = cache_expiry if cache_expiry is not None else self.expiry
        path = _make_cache_path(key)
        if os.path.exists(path):
            mtime = os.path.getmtime(path)
            if (time.time() - mtime) < cache_expiry:
                with open(path, "rb") as f:
                    return f.read()
        return None

    def save_preview(self, key: str, data: bytes):
        """Write PNG data to cache."""
        path = _make_cache_path(key)
        with open(path, "wb") as f:
            f.write(data)

    def clear_cache(self):
        """Remove all cached previews."""
        removed = 0
        for fname in os.listdir(self.cache_dir):
            if fname.endswith(".png"):
                try:
                    os.remove(os.path.join(self.cache_dir, fname))
                    removed += 1
                except Exception:
                    pass
        return removed

    def cache_stats(self) -> Dict[str, int]:
        """Return statistics: file count and total size."""
        count = 0
        size = 0
        for fname in os.listdir(self.cache_dir):
            if fname.endswith(".png"):
                count += 1
                size += os.path.getsize(os.path.join(self.cache_dir, fname))
        return {"files": count, "total_bytes": size}