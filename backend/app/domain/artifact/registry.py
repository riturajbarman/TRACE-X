"""Parser registration and lookup."""

from app.domain.artifact.parsers.base import BaseParser


class ParserRegistry:
    """Maintains a registry of available artifact parsers."""

    def __init__(self):
        self._parsers: dict[str, BaseParser] = {}

    def register(self, parser: BaseParser) -> None:
        """Register a parser for its supported artifact types."""
        for artifact_type in parser.supported_types:
            # For simplicity in MVP, one parser per type.
            # In a real system, you might have multiple and pick the best version.
            self._parsers[artifact_type] = parser

    def get_parser(self, artifact_type: str) -> BaseParser | None:
        """Look up a parser by artifact type."""
        return self._parsers.get(artifact_type)

    def list_parsers(self) -> list[dict]:
        """Return metadata for all registered parsers."""
        unique_parsers = set(self._parsers.values())
        return [
            {
                "name": p.name,
                "version": p.version,
                "supported_types": p.supported_types,
            }
            for p in unique_parsers
        ]
