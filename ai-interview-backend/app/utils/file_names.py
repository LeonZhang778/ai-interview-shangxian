import os
import re
import uuid


def sanitize_display_filename(filename: str, default: str = "file") -> str:
    """Return a display-safe basename without path components."""
    basename = os.path.basename(filename or "").strip()
    sanitized = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff._ -]+", "_", basename)
    sanitized = sanitized.strip(" ._")
    return sanitized or default


def safe_uuid_filename(filename: str, allowed_extensions: set[str], default_ext: str) -> tuple[str, str]:
    """Return (display_name, storage_filename) with a whitelisted extension."""
    display_name = sanitize_display_filename(filename)
    ext = os.path.splitext(display_name)[1].lower().lstrip(".")
    if ext not in allowed_extensions:
        ext = default_ext
    return display_name, f"{uuid.uuid4().hex}.{ext}"
