"""Sanitize upload filenames — never allow path traversal into temp/workdir paths."""
from __future__ import annotations

from pathlib import Path


class UnsafeFilenameError(ValueError):
    def __init__(self, message: str = "Unsafe upload filename") -> None:
        super().__init__(message)
        self.code = "UNSAFE_FILENAME"
        self.message = message


def safe_upload_basename(filename: str | None, *, default: str = "upload.bin") -> str:
    """Return a path-free basename; reject traversal / absolute / empty names."""
    raw = (filename or default).strip()
    if not raw:
        raise UnsafeFilenameError("Empty filename")
    # Normalize separators then take final component only
    normalized = raw.replace("\\", "/")
    if normalized.startswith("/") or (len(normalized) > 1 and normalized[1] == ":"):
        raise UnsafeFilenameError("Absolute upload paths are not allowed")
    if ".." in Path(normalized).parts or ".." in normalized.split("/"):
        raise UnsafeFilenameError("Path traversal in filename is not allowed")
    name = Path(normalized).name
    if not name or name in {".", ".."}:
        raise UnsafeFilenameError("Invalid upload filename")
    if len(name) > 200:
        raise UnsafeFilenameError("Filename too long")
    # Neutralize residual separators
    if "/" in name or "\\" in name:
        raise UnsafeFilenameError("Filename must not contain path separators")
    return name
