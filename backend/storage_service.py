"""Local filesystem storage helper for uploads."""
import logging
import os
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

APP_NAME = "scale-india"
STORAGE_ROOT = Path(
    os.environ.get("FILE_STORAGE_ROOT", Path(__file__).parent / "storage")
).resolve()


def init_storage() -> str:
    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    logger.info("File storage initialised at %s", STORAGE_ROOT)
    return str(STORAGE_ROOT)


def _resolve_storage_path(path: str) -> Path:
    relative_path = Path(path)
    target = (STORAGE_ROOT / relative_path).resolve()
    if STORAGE_ROOT not in target.parents and target != STORAGE_ROOT:
        raise RuntimeError("Invalid storage path")
    return target


def put_object(path: str, data: bytes, content_type: str) -> dict:
    init_storage()
    target = _resolve_storage_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return {
        "path": Path(path).as_posix(),
        "size": len(data),
        "content_type": content_type,
    }


def get_object(path: str) -> tuple[bytes, str]:
    init_storage()
    target = _resolve_storage_path(path)
    if not target.exists():
        raise FileNotFoundError(path)
    return target.read_bytes(), "application/octet-stream"


def build_upload_path(kind: str, ext: str) -> str:
    ext = (ext or "bin").lower().lstrip(".")
    return f"{APP_NAME}/{kind}/{uuid.uuid4()}.{ext}"
