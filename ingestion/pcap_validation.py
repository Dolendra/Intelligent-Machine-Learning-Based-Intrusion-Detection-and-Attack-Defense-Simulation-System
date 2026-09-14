"""PCAP upload validation for productionization Phase P1."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Any

# libpcap classic (LE/BE) and pcapng section header block magic
_PCAP_MAGICS = (
    b"\xd4\xc3\xb2\xa1",  # classic LE
    b"\xa1\xb2\xc3\xd4",  # classic BE
    b"\x4d\x3c\xb2\xa1",  # modified/nanosecond LE
    b"\xa1\xb2\x3c\x4d",  # modified/nanosecond BE
    b"\x0a\x0d\x0d\x0a",  # pcapng
)

_ALLOWED_SUFFIXES = {".pcap", ".pcapng", ".cap"}


@dataclass(frozen=True)
class PcapValidationResult:
    ok: bool
    code: str
    message: str
    size_bytes: int = 0
    sha256: str | None = None
    format_hint: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "code": self.code,
            "message": self.message,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "format_hint": self.format_hint,
        }


def max_pcap_bytes() -> int:
    """Default 25 MiB; override with IDS_PCAP_MAX_BYTES."""
    return int(os.getenv("IDS_PCAP_MAX_BYTES", str(25 * 1024 * 1024)))


def validate_pcap_upload(*, filename: str | None, content: bytes) -> PcapValidationResult:
    size = len(content)
    digest = hashlib.sha256(content).hexdigest() if content else None
    name = (filename or "capture.pcap").strip()

    # Path traversal / absolute path rejection (before extension checks)
    try:
        from ingestion.upload_safety import UnsafeFilenameError, safe_upload_basename

        safe_upload_basename(name, default="capture.pcap")
    except Exception as exc:  # noqa: BLE001
        code = getattr(exc, "code", "UNSAFE_FILENAME")
        return PcapValidationResult(
            False,
            str(code),
            getattr(exc, "message", str(exc)),
            size_bytes=size,
            sha256=digest,
        )

    suffix = ""
    if "." in name:
        suffix = "." + name.replace("\\", "/").rsplit(".", 1)[-1].lower()
        # If basename had path junk, suffix from raw name is still checked below

    if size == 0:
        return PcapValidationResult(False, "PCAP_EMPTY", "Uploaded PCAP is empty", size_bytes=0, sha256=digest)
    if size > max_pcap_bytes():
        return PcapValidationResult(
            False,
            "PCAP_TOO_LARGE",
            f"PCAP exceeds max size ({max_pcap_bytes()} bytes)",
            size_bytes=size,
            sha256=digest,
        )
    if suffix and suffix not in _ALLOWED_SUFFIXES:
        return PcapValidationResult(
            False,
            "PCAP_BAD_EXTENSION",
            f"Unsupported extension '{suffix}' (allowed: {sorted(_ALLOWED_SUFFIXES)})",
            size_bytes=size,
            sha256=digest,
        )
    if size < 24:
        return PcapValidationResult(
            False,
            "PCAP_TOO_SHORT",
            "File too short to be a valid PCAP/PCAPNG header",
            size_bytes=size,
            sha256=digest,
        )

    magic = content[:4]
    if magic not in _PCAP_MAGICS:
        return PcapValidationResult(
            False,
            "PCAP_BAD_MAGIC",
            "File magic does not match PCAP/PCAPNG",
            size_bytes=size,
            sha256=digest,
        )

    fmt = "pcapng" if magic == b"\x0a\x0d\x0d\x0a" else "pcap"
    return PcapValidationResult(
        True,
        "OK",
        "PCAP upload accepted for extraction",
        size_bytes=size,
        sha256=digest,
        format_hint=fmt,
    )
