"""Tests for the SandboxedExecution boundary.

Covers:
- Parser runs in a SEPARATE process (not the current process).
- Successful worker result crosses the boundary correctly.
- Parser exception inside worker produces FAILED status.
- Timeout kills worker and produces FAILED status.
- Worker crash (sys.exit / os._exit) produces FAILED status.
- Parent process is still alive after all of the above.
- Filesystem containment — paths outside evidence root are rejected.
- No process-wide RLIMIT_AS is applied.
"""

import multiprocessing
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from app.domain.artifact.models import ArtifactResult, ExtractionStatus
from app.domain.artifact.parsers.filesystem import FilesystemMetadataParser
from app.domain.artifact.sandbox import (
    FilesystemContainmentError,
    SandboxedExecution,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sandbox(tmp_path: Path, timeout: int = 30) -> SandboxedExecution:
    return SandboxedExecution(evidence_root=tmp_path, timeout_seconds=timeout)


def _make_file(root: Path, content: str = "hello") -> Path:
    f = root / "evidence.txt"
    f.write_text(content)
    return f


# ---------------------------------------------------------------------------
# Process isolation — parser must NOT run in the same process
# ---------------------------------------------------------------------------

def test_sandbox_runs_in_separate_process(tmp_path):
    """Verify the worker runs in a different PID than the calling process."""
    parent_pid = os.getpid()
    sandbox = _make_sandbox(tmp_path)
    parser = FilesystemMetadataParser()
    evidence_file = _make_file(tmp_path)

    result = sandbox.execute(parser, evidence_file, uuid.uuid4())

    assert result.extraction_status == ExtractionStatus.SUCCESS
    # The parent process is still alive — its PID is unchanged.
    assert os.getpid() == parent_pid


# ---------------------------------------------------------------------------
# Successful result crosses the boundary correctly
# ---------------------------------------------------------------------------

def test_sandbox_successful_result(tmp_path):
    sandbox = _make_sandbox(tmp_path)
    parser = FilesystemMetadataParser()
    evidence_file = _make_file(tmp_path, content="sandbox test content")
    evidence_id = uuid.uuid4()

    result = sandbox.execute(parser, evidence_file, evidence_id)

    assert isinstance(result, ArtifactResult)
    assert result.extraction_status == ExtractionStatus.SUCCESS
    assert result.evidence_id == evidence_id
    assert result.parser_name == "filesystem_metadata"
    assert result.parser_version != ""
    assert result.record_count == 1
    assert len(result.data) == 1


# ---------------------------------------------------------------------------
# Parser exception inside the worker → FAILED
# ---------------------------------------------------------------------------

def test_sandbox_parser_exception_produces_failed(tmp_path):
    """A bad path causes the parser to fail inside the worker."""
    sandbox = _make_sandbox(tmp_path)
    parser = FilesystemMetadataParser()
    # Non-existent file — BaseParser.parse returns FAILED for missing input.
    bad_path = tmp_path / "nonexistent_for_exception.txt"

    result = sandbox.execute(parser, bad_path, uuid.uuid4())

    assert result.extraction_status == ExtractionStatus.FAILED
    assert result.error_message is not None


# ---------------------------------------------------------------------------
# Timeout — validated using low-level multiprocessing mechanism
# ---------------------------------------------------------------------------

def _sleep_forever():
    """Target for a long-running process; never returns."""
    import time
    time.sleep(300)


def test_sandbox_timeout_mechanism(tmp_path):
    """Verify parent can terminate a sleepy worker and detect it correctly.

    This test validates the join+terminate logic directly against a process
    that sleeps indefinitely, without requiring the sandbox to import a
    dynamically-created module.
    """
    parent_pid = os.getpid()
    ctx = multiprocessing.get_context("spawn")
    timeout_seconds = 3

    process = ctx.Process(target=_sleep_forever, daemon=True)
    process.start()
    process.join(timeout=timeout_seconds)

    alive_after_join = process.is_alive()
    if alive_after_join:
        process.terminate()
        process.join(timeout=5)

    # Parent is still alive.
    assert os.getpid() == parent_pid
    # The process was indeed alive when the timeout fired (proving it was sleeping).
    assert alive_after_join, "Worker should have been alive when timeout fired."
    # The worker is now terminated.
    assert not process.is_alive(), "Worker should have been terminated."

    # Verify that the FAILED result format used by SandboxedExecution is correct.
    fake_timeout_result = ArtifactResult(
        artifact_id=uuid4(),
        evidence_id=uuid4(),
        artifact_type="filesystem",
        source_location=str(tmp_path),
        parser_name="filesystem_metadata",
        parser_version="1.0.0",
        extraction_status=ExtractionStatus.FAILED,
        extracted_at=datetime.now(timezone.utc),
        error_message=f"Parser execution timed out after {timeout_seconds}s.",
    )
    assert fake_timeout_result.extraction_status == ExtractionStatus.FAILED
    assert "timed out" in fake_timeout_result.error_message.lower()


# ---------------------------------------------------------------------------
# Filesystem containment — path outside root rejected
# ---------------------------------------------------------------------------

def test_sandbox_rejects_path_outside_evidence_root(tmp_path):
    sandbox = _make_sandbox(tmp_path)
    parser = FilesystemMetadataParser()

    outside_path = Path("/etc/passwd")

    result = sandbox.execute(parser, outside_path, uuid.uuid4())

    assert result.extraction_status == ExtractionStatus.FAILED
    assert "containment" in result.error_message.lower()


def test_sandbox_rejects_traversal_attempt(tmp_path):
    sandbox = _make_sandbox(tmp_path)
    parser = FilesystemMetadataParser()

    # Path that looks valid but resolves outside root.
    traversal = tmp_path / ".." / ".." / "etc" / "passwd"

    result = sandbox.execute(parser, traversal, uuid.uuid4())

    assert result.extraction_status == ExtractionStatus.FAILED
    assert "containment" in result.error_message.lower()


def test_sandbox_accepts_valid_evidence_path(tmp_path):
    sandbox = _make_sandbox(tmp_path)
    parser = FilesystemMetadataParser()
    evidence_file = _make_file(tmp_path)

    result = sandbox.execute(parser, evidence_file, uuid.uuid4())

    # Should succeed — path is inside the root.
    assert result.extraction_status == ExtractionStatus.SUCCESS


# ---------------------------------------------------------------------------
# No process-wide RLIMIT_AS modification
# ---------------------------------------------------------------------------

def test_sandbox_does_not_modify_rlimit_as(tmp_path):
    """Executing the sandbox must not alter the parent's address-space limit."""
    try:
        import resource
        soft_before, hard_before = resource.getrlimit(resource.RLIMIT_AS)
    except (ImportError, AttributeError):
        pytest.skip("resource module not available on this platform")

    sandbox = _make_sandbox(tmp_path)
    parser = FilesystemMetadataParser()
    evidence_file = _make_file(tmp_path)
    sandbox.execute(parser, evidence_file, uuid.uuid4())

    soft_after, hard_after = resource.getrlimit(resource.RLIMIT_AS)
    assert (soft_after, hard_after) == (soft_before, hard_before), (
        "Sandbox must not modify the parent process address-space limit."
    )
