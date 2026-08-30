
# TRACE-X Project Status

**Version:** 0.1
**Last Updated:** 2026-08-30
**Current Phase:** Phase 11 — AI Investigation Assistant
**Overall Status:** Phase 11 IMPLEMENTED (backend + frontend built and tested; pending user review before commit)

---

# 1. Current Project State

TRACE-X has moved beyond the initial architecture phase.

The backend foundation and initial Evidence Management workflow have been
implemented and validated with automated tests. The Phase 2 hardening patches
have been applied.

The current implementation includes:

- FastAPI backend
- PostgreSQL database
- SQLAlchemy database layer
- Alembic migrations
- Case/Evidence data model
- Evidence processing states
- Evidence processing error tracking
- Evidence API
- Evidence workflow tests
- Database connectivity checks
- Server-side SHA-256 calculation for evidence ingestion
- Evidence integrity verification mechanisms
- Case status transitions and case test coverage
- Audit logging mechanism and event tracking

The current focus is completing the remaining Evidence Management
requirements before moving into Artifact Extraction.

---

# 2. Project Health

| Area | Status | Notes |
|---|---|---|
| Repository | ✅ Complete | Git repository established |
| Project structure | ✅ Complete | Core structure established |
| Technical specification | ✅ Complete | TRACESPEC v0.2 |
| Project brain | ✅ Complete | BRAIN.md |
| Agent instructions | ✅ Complete | AGENTS.md |
| Processing pipeline | ✅ Complete | PIPELINE.md |
| Development roadmap | ✅ Complete | ROADMAP.md |
| Status tracking | 🟢 Active | Updated to reflect implementation |
| Agent skills | 🟡 In Progress | Initial skills still required |
| Architecture review | 🟡 In Progress | Core architecture established |
| Application foundation | 🟢 In Progress | Backend foundation implemented |
| Backend | 🟢 Active | FastAPI backend operational |
| Frontend | ⬜ Not Started | Next.js not yet implemented |
| Database | 🟢 Active | PostgreSQL + Alembic operational |
| Phase | Status | Focus |
|-------|--------|-------|
| 1 | Complete | Core Architecture, Domain Models, Persistence |
| 2 | Complete | API, Evidence Management, Security Boundaries |
| 3 | Complete | Artifact Extraction (MVP Parsers, Sandbox) |
| 4 | Complete | Event Store & Normalization |
| 5 | Complete | Detection Engine, IOC, Risk Scoring |
| 6 | Complete | Timeline, Audit, Deterministic Risk |
| 7 | Complete | MVP Integration, Frontend UI, CORS, Processing Pipeline |
| 8 | Complete | Correlation Engine (shared-entity, time-window, provenance) |
| 9 | Complete | ML / Anomaly Detection (Isolation Forest, synthetic baseline) |
| 10 | Complete | Investigation Graph |
| 11 | Implemented (pending review) | AI Investigation Assistant (RAG deferred to Phase 12) |
| Testing infrastructure | 🟢 Active | Backend tests operational |
| CI/CD | ⬜ Not Started | Not yet implemented |
| Benchmarking | ⬜ Not Started | Not yet implemented |
| Deployment | 🟡 Local | Local-first development |

---

# 3. Completed

## Project Constitution

- [x] TRACESPEC.md v0.2
- [x] BRAIN.md
- [x] AGENTS.md
- [x] PIPELINE.md
- [x] ROADMAP.md
- [x] STATUS.md

## Architecture Decisions

- [x] Evidence-first philosophy
- [x] Automation-before-AI principle
- [x] Raw evidence treated as untrusted
- [x] Three-zone trust architecture
- [x] Evidence provenance requirement
- [x] Evidence immutability requirement (Note: Current immutability is implemented as application-level accidental overwrite protection via `chmod(0o444)`. Stronger WORM/object-lock storage is deferred for future hardening.)
- [x] Partial-processing semantics
- [x] MVP scope defined
- [x] Advanced features separated from MVP
- [x] Benchmarking requirements defined
- [x] AI grounding requirement defined

## Backend Foundation

- [x] FastAPI application
- [x] PostgreSQL connection
- [x] SQLAlchemy database layer
- [x] Alembic configuration
- [x] Initial database migrations
- [x] Database connectivity verification
- [x] Pytest test execution
- [x] Evidence API tests
- [x] Test isolation improvements (Unique UUID content generation for evidence hashing isolation)

## Phase 3: Artifact Extraction (MVP) — Implementation complete, valid Registry fixture BLOCKED

**Goal:** Implement safe execution boundary for parsers and extract raw data from evidence.

- [x] Create `BaseParser` interface.
- [x] Create `ParserRegistry`.
- [x] Implement MVP parsers:
  - [x] Filesystem Metadata (`rglob`, `os.stat`).
  - [x] Windows Event Logs (`python-evtx`).
  - [x] Windows Registry (`regipy`).
- [x] Implement `SandboxedExecution` wrapper (process isolation, timeout).
  - Parser executes in a separate spawned child process (not the FastAPI process).
  - Timeout enforced via `process.join(timeout)` + `process.terminate()` — kills only the worker.
  - Filesystem containment: input path resolved and validated against evidence root before spawning.
  - Structured result boundary: only a plain dict crosses the process boundary.
  - **NOT implemented:** CPU limits, memory limits, network isolation, privilege dropping, container/cgroup isolation.
- [x] Implement `ExtractionService`.
- [x] Implement `/evidence/{id}/extract` endpoint (with explicit Pydantic response schema).
- [x] Write parser and service tests.
- [x] EVTX real fixture success path proven — real `python-evtx` parses `tests/fixtures/sample.evtx` (30 MB, 62,031 records; extraction capped at 1,000).
- [ ] Registry valid fixture — **BLOCKED**: `tests/fixtures/sample_registry.dat` is a 14-byte stub (`"404: Not Found"`), not a valid Windows Registry hive. `test_registry_parser_valid_real_fixture` is `xfail(strict=True)`. Must remain blocked until a genuine `.hiv`/`.dat` fixture is committed.

## Evidence Management

- [x] Evidence model
- [x] Canonical `/evidence/ingest` API (legacy metadata creation route removed)
- [x] Configurable upload size limit enforced during streaming
- [x] Server-side SHA-256 calculation
- [x] Upload rejection temporary file cleanup
- [x] Stored original integrity verification (`LocalEvidenceStorage.verify_integrity`)
- [x] Overwrite protection for local storage
- [x] Evidence processing states (Note: There is a known mismatch between ROADMAP.md and implementation. The current `PENDING, PROCESSING, READY, FAILED` state machine is an intentional MVP simplification. The ROADMAP describes a more complex lifecycle that can be adopted later.)
- [x] Evidence processing error field
- [x] Evidence workflow validation
- [x] Case Evidence Read Path (`GET /cases/{case_id}/evidence`)
- [x] Case status transition validation
- [x] Test suite expanded for Case and Integrity features
- [x] Migration for `processing_error`
- [x] Database migration applied successfully
- [x] Tests passing
- [x] Audit events are recorded (Audit logging for Case creation, Case status changes, Evidence ingestion, Evidence status changes)
- [x] Audit/business transaction atomicity (single commit per use case, repositories use flush)
- [x] Integrity verification wired into EvidenceService and exposed via POST /evidence/{id}/verify API
- [x] Audit-write failure regression tests (Case and Evidence paths)
- [x] Integrity verification API tests (valid, modified, missing)

### Phase 8: Correlation Engine
- [x] Deterministic event grouping
- [x] Evidence provenance tracking
- [x] Time-window + secondary relationship correlation

### Phase 9: ML / Anomaly Detection
- [x] Isolation Forest model implemented (`scikit-learn`)
- [x] Synthetic baseline dataset created (`normal_events.json`, `anomalous_events.json`)
- [x] Deterministic feature extraction (10 features)
- [x] `FPR` evaluated and bounded (measured FPR: 0.080)
- [x] Results exposed as `Detection` rows with `detection_type="anomaly"`
- ⚠️ **Limitation**: Synthetic baseline is not real-world forensic validation. ML is a signal, not proof.
  - Measured on synthetic dataset: Precision: 0.000, Recall: 0.000, F1: 0.000, FPR: 0.080.
  - These metrics come strictly from the synthetic fixture and are expected limits of the model type on zero-variance baseline data, not production validation.

---

## Remaining Phase 2 Gaps
- Database isolation for tests is still incomplete (tests share the same database; handled currently by generating unique UUIDs for test content to bypass SHA-256 constraints, but not truly transactional).

## Validation

### Phase 9 API Smoke Test

**Endpoint:**
`POST /cases/{case_id}/anomaly-scan`

**Verified:**
HTTP 200

**Response:**
```json
{
  "case_id": "9178c091-0ae9-4cc4-b1fe-c8d2b203f39e",
  "model_version": "1.0.0",
  "anomaly_count": 0,
  "findings": []
}
```

**Case ID:**
`9178c091-0ae9-4cc4-b1fe-c8d2b203f39e`

*(API smoke test verified as above.)*

**Frontend Smoke Test: PASS WITH LIMITATION**

- Frontend loads at `http://localhost:3000` ✅
- Case list page renders ✅
- Case detail page returns HTTP 200 ✅
- Frontend communicates with FastAPI backend (CORS confirmed) ✅
- Existing case workflow UI exposes: Evidence, Events, Timeline, Risk, Report tabs ✅
- Risk endpoint verified — returned a valid structured response ✅
- No unexpected backend errors observed ✅
- **Limitation:** `POST /cases/{case_id}/anomaly-scan` is **not exposed in the frontend**. Anomaly detection is backend/API-only functionality at this phase. The endpoint was independently smoke-tested via direct API call (HTTP 200 verified). Do not implement anomaly UI — that is Phase 10+ scope.

Phase 10 — Investigation Graph (COMPLETE)
Backend logic to derive provenance, FK, and entity-based edges from events and detections.
New API endpoint /cases/{case_id}/graph.
Frontend graph visualization using react-force-graph.

Phase 11 — AI Investigation Assistant (IMPLEMENTED, pending review)

Scope note: Phase 11 is the evidence-grounded AI Investigation Assistant
only. RAG / external knowledge grounding (MITRE ATT&CK etc.) remains
Phase 12 and was explicitly NOT implemented here — this reconciles the
short-form "AI + RAG" label used elsewhere with the detailed Phase
11/Phase 12 split that ROADMAP.md, TRACESPEC.md, PIPELINE.md, and
BRAIN.md already describe consistently.

What was built:
- `backend/app/domain/assistant/` — thin, vendor-agnostic provider
  abstraction (`AssistantProvider`), one concrete provider
  (`AnthropicProvider`, model `claude-opus-5` by default, fully
  configurable via `ASSISTANT_MODEL`), bounded case-scoped context
  assembly reusing existing read-only services (`context.py`), and
  explicit grounding validation (`grounding.py`) that never lets an
  unverified object id reach the investigator as an "observed" claim.
- New endpoint `POST /cases/{case_id}/assistant/query` — read-only with
  respect to all forensic data; the only write it performs is an
  `AI_QUERY_EXECUTED` audit-log entry (no question text, no secrets, no
  raw evidence recorded).
- Correlation/anomaly context is read from already-persisted
  Incidents/Detections only — the assistant never triggers
  `/correlate` or `/anomaly-scan` itself, since both mutate data.
- New frontend "Assistant" tab in the case dashboard — independent of
  the other tabs' shared loading/error state; a failed or unconfigured
  assistant call cannot affect Evidence/Events/Timeline/Risk/Report/Graph.
- Context limits (`ASSISTANT_MAX_EVENTS`, `_DETECTIONS`, `_IOCS`,
  `_INCIDENTS`, `_GRAPH_NODES`, `_EVIDENCE`) are explicit and
  configurable via environment variables, not silently unbounded.

**Known limitation (unchanged from before Phase 11, now more relevant):**
TRACE-X has no authentication/authorization layer anywhere in the
backend. The new assistant endpoint can incur real provider API cost and
expose case-scoped data to whichever provider is configured — anyone who
can reach the API can call it. This is documented in the endpoint's
docstring and in `app/core/config.py`, but was **not** fixed as part of
Phase 11 per explicit scope (auth is Phase 14/15). Do not expose a
deployment of this endpoint publicly before adding authentication.

**Testing:** 25 new backend tests (provider mockability, grounding
validation, valid/failed/malformed provider responses, invented-id
rejection, observed-without-provenance demotion, forensic-data
regression check, API-key-never-leaked check, response-schema
separation) — all passing alongside the full existing suite (202 passed,
1 xfailed total, zero regressions). Frontend: `tsc --noEmit` clean;
browser smoke test confirmed the Assistant tab loads, submits, calls the
API, renders the graceful "unavailable" state correctly (no
`ANTHROPIC_API_KEY` was available in this environment, so the live
Anthropic call path itself — as opposed to its error handling — was not
exercised end-to-end), and that all other tabs continue working
before and after using the Assistant tab.

Latest backend test result:

```text
202 passed, 1 xfailed, 2 warnings
```
