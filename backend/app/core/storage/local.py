import hashlib
from pathlib import Path
from shutil import copyfile
from uuid import UUID


class LocalEvidenceStorage:
    """Local filesystem storage for immutable original evidence."""

    def __init__(self, root_path: str):
        self.root_path = Path(root_path).expanduser().resolve()
        self.root_path.mkdir(parents=True, exist_ok=True)

    def _evidence_directory(self, evidence_id: UUID) -> Path:
        directory = (self.root_path / str(evidence_id)).resolve()
        if not directory.is_relative_to(self.root_path):
            raise ValueError(f"Path escape attempt: {evidence_id}")
        return directory

    def original_path(self, evidence_id: UUID) -> Path:
        path = (self._evidence_directory(evidence_id) / "original").resolve()
        if not path.is_relative_to(self.root_path):
            raise ValueError(f"Path escape attempt: {evidence_id}")
        return path

    def exists(self, evidence_id: UUID) -> bool:
        return self.original_path(evidence_id).is_file()

    def save_original(self, evidence_id: UUID, source_path: Path) -> Path:
        destination = self.original_path(evidence_id)

        if destination.exists():
            raise FileExistsError(
            f"Original evidence already exists: {evidence_id}"
        )

        if not source_path.is_file() or source_path.is_symlink():
            raise FileNotFoundError(
                f"Source evidence not found or is not a regular file: {source_path}"
            )

        destination.parent.mkdir(parents=True, exist_ok=True)

        with source_path.open("rb") as source, destination.open("xb") as target:
            while chunk := source.read(1024 * 1024):
                target.write(chunk)

        destination.chmod(0o444)

        return destination

    def open_original(self, evidence_id: UUID):
        path = self.original_path(evidence_id)

        if not path.is_file():
            raise FileNotFoundError(
                f"Original evidence not found: {evidence_id}"
            )

        return path.open("rb")
    def delete_original(self, evidence_id: UUID) -> None:
        path = self.original_path(evidence_id)

        if path.exists():
            path.unlink()

        parent = path.parent

        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()

    def verify_integrity(self, evidence_id: UUID, expected_sha256: str) -> bool:
        path = self.original_path(evidence_id)

        if not path.is_file():
            raise FileNotFoundError(f"Original evidence not found: {evidence_id}")

        sha256 = hashlib.sha256()
        with path.open("rb") as f:
            while chunk := f.read(1024 * 1024):
                sha256.update(chunk)

        return sha256.hexdigest() == expected_sha256
