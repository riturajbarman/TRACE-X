from app.core.config import STORAGE_BACKEND, STORAGE_PATH
from app.core.storage.local import LocalEvidenceStorage


def get_evidence_storage() -> LocalEvidenceStorage:
    if STORAGE_BACKEND != "local":
        raise ValueError(
            f"Unsupported storage backend: {STORAGE_BACKEND}"
        )

    return LocalEvidenceStorage(STORAGE_PATH)