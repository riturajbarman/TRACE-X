from pathlib import Path
import hashlib


def calculate_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Calculate the SHA-256 hash of a file."""
    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    digest = hashlib.sha256()

    with path.open("rb") as file:
        while chunk := file.read(chunk_size):
            digest.update(chunk)

    return digest.hexdigest()