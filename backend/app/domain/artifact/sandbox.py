"""Sandboxed execution boundary for artifact parsers.

Isolation strategy (Phase 3 MVP):

  - IMPLEMENTED:   Process isolation via multiprocessing.Process (spawn context).
  - IMPLEMENTED:   Timeout — parent kills worker after ``timeout_seconds``.
  - IMPLEMENTED:   Filesystem containment — input path checked against evidence root
                   before the worker is started; traversal attempts are rejected.
  - NOT IMPLEMENTED: Network isolation (no portable mechanism without OS primitives).
  - NOT IMPLEMENTED: Privilege dropping (requires OS-specific seccomp/setuid).
  - NOT IMPLEMENTED: Container / cgroup isolation.

The parser runs in a freshly spawned child process. The child communicates
its result back to the parent via a ``multiprocessing.Queue``.  If the child
exits unexpectedly (crash) or exceeds the timeout the parent returns a FAILED
result without affecting the FastAPI process.

No process-wide resource limits (RLIMIT_AS) are applied to the parent process.
"""

import multiprocessing
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from app.domain.artifact.models import ArtifactResult, ExtractionStatus
from app.domain.artifact.parsers.base import BaseParser

# Use "spawn" context so the child process starts fresh (no inherited state).
# This is the default on macOS and Windows; on Linux it defaults to "fork"
# which can cause problems with some C-extension libraries.
_MP_CONTEXT = multiprocessing.get_context("spawn")


def _worker(
    parser_class_module: str,
    parser_class_name: str,
    input_path_str: str,
    evidence_id_str: str,
    result_queue,
) -> None:
    """Entry point for the extraction worker process.

    This runs in a *separate* process. It imports the parser class, executes
    it, and puts the structured result dict onto the queue.

    Only plain, picklable data crosses the process boundary.
    """
    import importlib
    from datetime import datetime, timezone
    from pathlib import Path
    from uuid import UUID, uuid4

    from app.domain.artifact.models import ArtifactResult, ExtractionStatus

    input_path = Path(input_path_str)
    evidence_id = UUID(evidence_id_str)

    try:
        module = importlib.import_module(parser_class_module)
        parser_cls = getattr(module, parser_class_name)
        parser = parser_cls()

        result: ArtifactResult = parser.parse(input_path, evidence_id)
    except Exception as exc:
        result = ArtifactResult(
            artifact_id=uuid4(),
            evidence_id=evidence_id,
            artifact_type="unknown",
            source_location=input_path_str,
            parser_name=parser_class_name,
            parser_version="unknown",
            extraction_status=ExtractionStatus.FAILED,
            extracted_at=datetime.now(timezone.utc),
            error_message=f"Worker error: {type(exc).__name__}: {exc}",
        )

    # Serialise to a plain dict so it crosses the process boundary safely.
    result_queue.put({
        "artifact_id": str(result.artifact_id),
        "evidence_id": str(result.evidence_id) if result.evidence_id else None,
        "artifact_type": result.artifact_type,
        "source_location": result.source_location,
        "parser_name": result.parser_name,
        "parser_version": result.parser_version,
        "extraction_status": result.extraction_status.value,
        "extracted_at": result.extracted_at.isoformat(),
        "data": result.data,
        "record_count": result.record_count,
        "error_message": result.error_message,
    })


def _dict_to_result(d: dict) -> ArtifactResult:
    """Reconstruct an ArtifactResult from the serialised worker dict."""
    from datetime import datetime, timezone
    from uuid import UUID

    return ArtifactResult(
        artifact_id=UUID(d["artifact_id"]) if d.get("artifact_id") else uuid4(),
        evidence_id=UUID(d["evidence_id"]) if d.get("evidence_id") else None,
        artifact_type=d.get("artifact_type", ""),
        source_location=d.get("source_location", ""),
        parser_name=d.get("parser_name", ""),
        parser_version=d.get("parser_version", ""),
        extraction_status=ExtractionStatus(d.get("extraction_status", "FAILED")),
        extracted_at=datetime.fromisoformat(d["extracted_at"]) if d.get("extracted_at") else datetime.now(timezone.utc),
        data=d.get("data", []),
        record_count=d.get("record_count", 0),
        error_message=d.get("error_message"),
    )


class FilesystemContainmentError(Exception):
    """Raised when an input path escapes the permitted evidence root."""


class SandboxedExecution:
    """Executes a parser inside an isolated child process.

    Parameters
    ----------
    evidence_root:
        Canonical evidence storage root. All input paths must resolve to a
        location inside this directory.
    timeout_seconds:
        Maximum wall-clock seconds to allow the worker before the parent
        terminates it. Defaults to 60 s.
    """

    def __init__(self, evidence_root: Path, timeout_seconds: int = 60):
        self.evidence_root = Path(evidence_root).resolve()
        self.timeout_seconds = timeout_seconds

    # ------------------------------------------------------------------
    # Filesystem containment
    # ------------------------------------------------------------------

    def _check_containment(self, input_path: Path) -> Path:
        """Return the resolved path or raise ``FilesystemContainmentError``."""
        resolved = input_path.resolve()
        # is_relative_to is available from Python 3.9+.
        try:
            resolved.relative_to(self.evidence_root)
        except ValueError:
            raise FilesystemContainmentError(
                f"Path escapes evidence root. Resolved: {resolved}, "
                f"Root: {self.evidence_root}"
            )
        return resolved

    # ------------------------------------------------------------------
    # Main execution entry point
    # ------------------------------------------------------------------

    def execute(
        self,
        parser: BaseParser,
        input_path: Path,
        evidence_id: UUID,
    ) -> ArtifactResult:
        """Run ``parser`` in a separate process and return the result.

        Guarantees:
        - The parser runs in a spawned child process, NOT in the FastAPI process.
        - The child is killed if it exceeds ``timeout_seconds``.
        - Filesystem containment is validated before spawning.
        - Only structured, serialised data crosses the boundary.
        """

        # 1. Filesystem containment check (before spawning anything).
        try:
            safe_path = self._check_containment(input_path)
        except FilesystemContainmentError as exc:
            return ArtifactResult(
                artifact_id=uuid4(),
                evidence_id=evidence_id,
                artifact_type=parser.supported_types[0] if parser.supported_types else "unknown",
                source_location=str(input_path),
                parser_name=parser.name,
                parser_version=parser.version,
                extraction_status=ExtractionStatus.FAILED,
                extracted_at=datetime.now(timezone.utc),
                error_message=f"Containment violation: {exc}",
            )

        # 2. Prepare worker arguments (only primitive/picklable values).
        parser_module = type(parser).__module__
        parser_class = type(parser).__name__
        result_queue = _MP_CONTEXT.Queue()

        # 3. Spawn the worker.
        process = _MP_CONTEXT.Process(
            target=_worker,
            args=(
                parser_module,
                parser_class,
                str(safe_path),
                str(evidence_id),
                result_queue,
            ),
            daemon=True,
        )
        process.start()

        # 4. Wait with timeout. If the timeout fires, terminate the worker.
        process.join(timeout=self.timeout_seconds)

        if process.is_alive():
            process.terminate()
            process.join(timeout=5)  # Give it a moment to clean up.
            return ArtifactResult(
                artifact_id=uuid4(),
                evidence_id=evidence_id,
                artifact_type=parser.supported_types[0] if parser.supported_types else "unknown",
                source_location=str(safe_path),
                parser_name=parser.name,
                parser_version=parser.version,
                extraction_status=ExtractionStatus.FAILED,
                extracted_at=datetime.now(timezone.utc),
                error_message=f"Parser execution timed out after {self.timeout_seconds}s.",
            )

        # 5. Check exit code — a non-zero exit means the worker crashed.
        if process.exitcode != 0:
            return ArtifactResult(
                artifact_id=uuid4(),
                evidence_id=evidence_id,
                artifact_type=parser.supported_types[0] if parser.supported_types else "unknown",
                source_location=str(safe_path),
                parser_name=parser.name,
                parser_version=parser.version,
                extraction_status=ExtractionStatus.FAILED,
                extracted_at=datetime.now(timezone.utc),
                error_message=f"Worker process crashed (exit code {process.exitcode}).",
            )

        # 6. Retrieve structured result from the queue.
        if result_queue.empty():
            return ArtifactResult(
                artifact_id=uuid4(),
                evidence_id=evidence_id,
                artifact_type=parser.supported_types[0] if parser.supported_types else "unknown",
                source_location=str(safe_path),
                parser_name=parser.name,
                parser_version=parser.version,
                extraction_status=ExtractionStatus.FAILED,
                extracted_at=datetime.now(timezone.utc),
                error_message="Worker exited without returning a result.",
            )

        raw = result_queue.get_nowait()

        # 7. Validate and reconstruct the result on the parent side.
        try:
            return _dict_to_result(raw)
        except Exception as exc:
            return ArtifactResult(
                artifact_id=uuid4(),
                evidence_id=evidence_id,
                artifact_type=parser.supported_types[0] if parser.supported_types else "unknown",
                source_location=str(safe_path),
                parser_name=parser.name,
                parser_version=parser.version,
                extraction_status=ExtractionStatus.FAILED,
                extracted_at=datetime.now(timezone.utc),
                error_message=f"Failed to deserialise worker result: {exc}",
            )
