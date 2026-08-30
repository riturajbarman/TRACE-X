import os

from dotenv import load_dotenv


load_dotenv()


STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")
STORAGE_PATH = os.getenv("STORAGE_PATH", "./evidence-data")
MAX_UPLOAD_SIZE_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", 50 * 1024 * 1024))

# Allowed browser origins for CORS — comma-separated list.
# Default covers the local Next.js dev server.
# Override in production via environment variable, never use "*" in production.
_cors_raw = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
CORS_ALLOWED_ORIGINS: list[str] = [o.strip() for o in _cors_raw.split(",") if o.strip()]

# Phase 11 — AI Investigation Assistant.
#
# Provider credentials are read only from the environment — never
# hardcoded, never committed. ASSISTANT_API_KEY is unset by default, which
# leaves the assistant endpoint in a graceful "unavailable" state rather
# than raising on every request (see app.domain.assistant.provider).
#
# KNOWN LIMITATION: there is currently no authentication/authorization
# anywhere in the TRACE-X backend. The assistant endpoint below can incur
# provider API cost and expose case-scoped data to whichever provider is
# configured, and today anyone who can reach this API can call it. Do not
# expose a deployment of this endpoint publicly before adding auth.
ASSISTANT_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ASSISTANT_MODEL = os.getenv("ASSISTANT_MODEL", "claude-opus-5")
ASSISTANT_PROVIDER_TIMEOUT_SECONDS = float(os.getenv("ASSISTANT_PROVIDER_TIMEOUT_SECONDS", "30"))

# Bounded, case-scoped context limits for the assistant — explicit and
# configurable rather than silently growing with database size. See
# app.domain.assistant.context.build_context for how each is applied.
ASSISTANT_MAX_EVENTS = int(os.getenv("ASSISTANT_MAX_EVENTS", "40"))
ASSISTANT_MAX_DETECTIONS = int(os.getenv("ASSISTANT_MAX_DETECTIONS", "40"))
ASSISTANT_MAX_IOCS = int(os.getenv("ASSISTANT_MAX_IOCS", "40"))
ASSISTANT_MAX_INCIDENTS = int(os.getenv("ASSISTANT_MAX_INCIDENTS", "20"))
ASSISTANT_MAX_GRAPH_NODES = int(os.getenv("ASSISTANT_MAX_GRAPH_NODES", "40"))
ASSISTANT_MAX_EVIDENCE = int(os.getenv("ASSISTANT_MAX_EVIDENCE", "50"))

# Phase 12 — external knowledge grounding (RAG Knowledge Layer).
#
# Deterministic lookup over a versioned, bundled, read-only static
# snapshot (MITRE ATT&CK) — no vector database, no embeddings, no network
# access at query time. See app.domain.knowledge for the full design
# rationale. Bounded and configurable, matching the ASSISTANT_MAX_*
# convention above — never silently unbounded.
KNOWLEDGE_MAX_RESULTS = int(os.getenv("KNOWLEDGE_MAX_RESULTS", "5"))
KNOWLEDGE_MAX_CONTEXT_CHARS = int(os.getenv("KNOWLEDGE_MAX_CONTEXT_CHARS", "4000"))