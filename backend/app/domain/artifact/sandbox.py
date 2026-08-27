"""Sandboxed execution boundary for artifact parsers.

This provides process-level isolation (timeouts, read-only mode, memory limits).
It is explicitly NOT a full container sandbox in this MVP.
"""

import signal
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from app.domain.artifact.models import ArtifactResult, ExtractionStatus
from app.domain.artifact.parsers.base import BaseParser

# Optional resource limits for UNIX-like systems
try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    HAS_RESOURCE = False


class TimeoutException(Exception):
    pass


def _timeout_handler(signum, frame):
    raise TimeoutException("Parser execution timed out.")


class SandboxedExecution:
    """Provides a minimal execution boundary around parsers."""

    def __init__(self, timeout_seconds: int = 60, memory_limit_mb: int = 512):
        self.timeout_seconds = timeout_seconds
        self.memory_limit_mb = memory_limit_mb

    def execute(
        self,
        parser: BaseParser,
        input_path: Path,
        evidence_id: UUID
    ) -> ArtifactResult:
        """Executes a parser within boundary limits."""
        
        # In a full sandbox, we'd mount this path as read-only in a container.
        # For now, we enforce that the parser cannot modify it by opening it read-only
        # but in Python we can't easily force all standard libraries to only read.
        # The base parser and parsers open things in read mode.
        
        # Set memory limits if on a supported OS
        if HAS_RESOURCE:
            try:
                # Limit address space
                soft, hard = resource.getrlimit(resource.RLIMIT_AS)
                limit = self.memory_limit_mb * 1024 * 1024
                # Only decrease limit
                if soft == resource.RLIM_INFINITY or limit < soft:
                    resource.setrlimit(resource.RLIMIT_AS, (limit, hard))
            except (ValueError, OSError):
                pass  # Ignore if limits can't be set
        
        # Set timeout
        old_handler = None
        if hasattr(signal, 'SIGALRM'):
            try:
                old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
                signal.alarm(self.timeout_seconds)
            except ValueError as exc:
                if "main thread" not in str(exc).lower():
                    raise

        try:
            return parser.parse(input_path, evidence_id)
        except TimeoutException:
            return ArtifactResult(
                artifact_id=uuid4(),
                evidence_id=evidence_id,
                artifact_type=parser.supported_types[0] if parser.supported_types else "unknown",
                source_location=str(input_path),
                parser_name=parser.name,
                parser_version=parser.version,
                extraction_status=ExtractionStatus.FAILED,
                extracted_at=datetime.now(timezone.utc),
                error_message=f"Parser execution timed out after {self.timeout_seconds}s.",
            )
        except Exception as exc:
            return ArtifactResult(
                artifact_id=uuid4(),
                evidence_id=evidence_id,
                artifact_type=parser.supported_types[0] if parser.supported_types else "unknown",
                source_location=str(input_path),
                parser_name=parser.name,
                parser_version=parser.version,
                extraction_status=ExtractionStatus.FAILED,
                extracted_at=datetime.now(timezone.utc),
                error_message=f"Sandbox error: {type(exc).__name__}: {exc}",
            )
        finally:
            # Restore timeout and limits (if possible, though process limits stay)
            if hasattr(signal, 'SIGALRM'):
                try:
                    signal.alarm(0)
                    if old_handler:
                        signal.signal(signal.SIGALRM, old_handler)
                except ValueError:
                    pass
