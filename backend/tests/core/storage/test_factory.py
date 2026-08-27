from app.core.storage.factory import get_evidence_storage
from app.core.storage.local import LocalEvidenceStorage


def test_get_evidence_storage_returns_local_storage():
    storage = get_evidence_storage()

    assert isinstance(storage, LocalEvidenceStorage)