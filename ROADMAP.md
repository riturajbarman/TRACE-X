# TRACE-X Development Roadmap

**Version:** 0.1  
**Purpose:** Define the development journey of TRACE-X  
**Last Updated:** 2026-08-26

---

# 1. Roadmap Philosophy

TRACE-X will be developed as a long-term engineering project rather
than a short hackathon prototype.

The development strategy is:

```text
Understand
   ↓
Specify
   ↓
Architect
   ↓
Foundation
   ↓
MVP
   ↓
Validation
   ↓
Advanced Intelligence
   ↓
Performance
   ↓
Benchmarking
   ↓
Release
```

The project will prioritize:

- Correctness
- Security
- Evidence integrity
- Testing
- Measurable results
- Maintainability
- Real functionality

Features will not be added simply because they look impressive.

---

# 2. Development Stages

```text
PHASE 0  → Research & Architecture
PHASE 1  → Project Foundation
PHASE 2  → Evidence Management
PHASE 3  → Artifact Extraction
PHASE 4  → Event Model & Event Store
PHASE 5  → Detection Engine
PHASE 6  → Timeline & Risk
PHASE 7  → MVP Integration
PHASE 8  → Correlation Engine
PHASE 9  → ML / Anomaly Detection
PHASE 10 → Investigation Graph
PHASE 11 → AI + RAG
PHASE 12 → Investigator Dashboard
PHASE 13 → Reporting & Export
PHASE 14 → Security Hardening
PHASE 15 → Testing & Benchmarking
PHASE 16 → Performance & Scale
PHASE 17 → Release / Open Source / SIH
```

---

# 3. Phase 0 — Research & Architecture

## Goal

Understand the problem deeply before implementation.

## Tasks

- Study digital forensics fundamentals.
- Study DFIR workflows.
- Study Windows forensic artifacts.
- Study existing solutions.
- Finalize TRACESPEC.
- Finalize BRAIN.
- Finalize AGENTS.
- Finalize PIPELINE.
- Define roadmap.
- Define project status model.
- Define AI-agent workflow.
- Define initial project skills.
- Define core data model.
- Define trust boundaries.
- Define evidence integrity strategy.
- Define testing methodology.

## Deliverables

```text
TRACESPEC.md
BRAIN.md
AGENTS.md
PIPELINE.md
ROADMAP.md
STATUS.md
Initial Skills
Architecture Decisions
```

## Definition of Done

- Core architecture is documented.
- Data model is sufficiently defined for implementation.
- Trust boundaries are documented.
- MVP scope is agreed.
- Testing strategy is defined.
- No major unresolved architectural contradiction remains.

---

# 4. Phase 1 — Project Foundation

## Goal

Create a clean, reproducible development environment.

## Tasks

- Next.js frontend
- FastAPI backend
- PostgreSQL
- Redis
- Docker
- Docker Compose
- Environment configuration
- Logging
- Basic testing infrastructure
- Basic CI
- Frontend/backend connectivity
- Backend/database connectivity

## Deliverable

```text
Browser
   ↓
Next.js
   ↓
FastAPI
   ↓
PostgreSQL
```

All components run locally using the documented setup.

## Definition of Done

- Fresh clone can be started using documented instructions.
- Frontend runs.
- Backend runs.
- Database connects.
- Health endpoint works.
- Basic tests pass.
- Docker environment works.
- No secrets are committed.

---

# 5. Phase 2 — Evidence Management

## Goal

Build the secure evidence lifecycle.

## Tasks

- Case creation
- Evidence ingestion
- Evidence metadata
- SHA-256 hashing
- Evidence storage
- Integrity status
- Processing states
- Provenance tracking
- Basic audit logging

## Initial states

```text
CREATED
QUEUED
PROCESSING
PARTIAL
COMPLETED
FAILED
CANCELLED
```

## Definition of Done

- Evidence can be associated with a Case.
- SHA-256 is calculated.
- Original evidence is protected from modification.
- Metadata is stored.
- Processing state is tracked.
- Integrity failures are visible.
- Tests cover normal and failure cases.
- Audit events are recorded.

---

# 6. Phase 3 — Artifact Extraction

## Goal

Build the first real forensic analysis capabilities.

## MVP artifact types

1. Filesystem metadata
2. Windows Event Logs
3. Windows Registry

## Tasks

- Parser interface
- Parser registration
- Parser versioning
- Sandboxed execution
- Input validation
- Resource limits
- Timeouts
- Extraction status
- Error handling
- Provenance

## Definition of Done

For every MVP parser:

- Valid fixture works.
- Empty input handled.
- Corrupt input handled.
- Unsupported input handled.
- Parser errors are recorded.
- Parser version is recorded.
- Extracted data preserves provenance.
- Tests pass.

---

# 7. Phase 4 — Event Model & Event Store

## Goal

Create the trusted analytical foundation.

## Tasks

- Finalize Event schema.
- Finalize Case/Evidence/Artifact relationships.
- PostgreSQL schema.
- Database migrations.
- Indexing strategy.
- Event persistence.
- Query layer.
- Event validation.
- Schema versioning.

## Definition of Done

- Every normalized event references its source artifact.
- Every event can be traced to evidence.
- Events can be queried efficiently.
- Schema migrations work.
- Compatibility tests exist.
- Large event collections can be stored and queried reliably.

---

# 8. Phase 5 — Detection Engine

## Goal

Turn raw normalized events into useful findings.

## 5.1 IOC Engine

Implement deterministic detection for supported:

- IPs
- Domains
- URLs
- Hashes
- Filenames
- Registry indicators

## 5.2 Rule Engine

Create an initial set of versioned rules.

Each rule should define:

- Rule ID
- Rule name
- Description
- Input conditions
- Severity
- Confidence
- Version
- Supporting evidence requirements

## Definition of Done

- IOCs are detected correctly.
- Rules are versioned.
- Detections preserve provenance.
- Detection explanations are available.
- Test fixtures have known ground truth.
- False-positive tests exist.

---

# 9. Phase 6 — Timeline & Risk

## Goal

Turn detections and events into an investigator-friendly view.

## Timeline

Implement:

- Chronological event ordering
- Time filters
- Source filters
- Severity filters
- Incident filters
- Evidence references

## Risk Engine

Start with deterministic scoring.

Potential signals:

- IOC
- Rule detection
- Persistence
- Network activity
- Correlation
- Context

## Definition of Done

- Timeline displays real normalized events.
- Events can be filtered.
- Every finding links back to evidence.
- Risk score has a documented formula.
- Risk explanation shows contributing signals.
- Score is tested against controlled cases.

---

# 10. Phase 7 — MVP Integration

## Goal

Create the first genuinely usable TRACE-X system.

The complete MVP flow:

```text
Case
 ↓
Evidence
 ↓
Hash
 ↓
Sandbox
 ↓
Artifact Extraction
 ↓
Normalization
 ↓
Event Store
 ↓
IOC Detection
 ↓
Rule Detection
 ↓
Timeline
 ↓
Basic Risk
 ↓
JSON / PDF Report
```

## Definition of Done

A controlled forensic case can move through the complete MVP pipeline
without manual database intervention.

The investigator can:

1. Create a case.
2. Add evidence.
3. Run processing.
4. View extracted artifacts.
5. View events.
6. View IOCs.
7. View detections.
8. View the timeline.
9. View risk.
10. Generate a report.

---

# 11. Phase 8 — Correlation Engine

## Goal

Move from isolated findings to related activity.

## Initial approach

Start with deterministic correlation:

- Shared entities
- Time windows
- Process relationships
- File relationships
- Network relationships
- Provenance

## Example

```text
PowerShell
   ↓
File creation
   ↓
Network connection
   ↓
Persistence
```

## Definition of Done

- Related events can be grouped.
- Correlation relationships are explainable.
- Supporting evidence is preserved.
- Correlation results are testable.
- False correlations are measured.

---

# 12. Phase 9 — ML / Anomaly Detection

## Goal

Identify behaviour that is unusual relative to a defined baseline.

## Tasks

- Define baseline.
- Define features.
- Create training/evaluation datasets.
- Implement baseline model.
- Start with classical ML.
- Measure precision/recall.
- Measure false positives.
- Provide explanations.

Potential initial algorithm:

```text
Isolation Forest
```

## Definition of Done

- Baseline is explicitly documented.
- Dataset is documented.
- Features are documented.
- Model versioning exists.
- Evaluation metrics are measured.
- False-positive rate is measured.
- ML output is clearly represented as an anomaly signal.

---

# 13. Phase 10 — Investigation Graph

## Goal

Visualize relationships between investigation entities.

## Example

```text
User
 ↓
Process
 ↓
File
 ↓
Hash
 ↓
IP
 ↓
Registry
```

## Tasks

- Graph data model
- Relationship extraction
- Graph API
- Interactive UI
- Node filtering
- Evidence references

## Definition of Done

- Graph represents real investigation data.
- Important relationships are traceable to evidence.
- No fabricated graph relationships exist.
- Large graphs remain usable.

---

# 14. Phase 11 — AI Investigation Assistant

## Goal

Help investigators reason about already-processed data.

## Tasks

- Structured evidence retrieval
- Investigation query layer
- Prompt architecture
- Claim/evidence linking
- Response validation
- Uncertainty handling
- Local-model support where practical
- Optional external LLM providers

## AI must distinguish

```text
Observed Evidence
Inference
Recommendation
```

## Definition of Done

- AI can answer questions about processed cases.
- Factual claims link to TRACE-X objects.
- Missing evidence is acknowledged.
- Hallucination tests exist.
- AI does not have direct unrestricted access to raw evidence.
- AI functionality can fail without breaking core forensics.

---

# 15. Phase 12 — RAG Knowledge Layer

## Goal

Add contextual cybersecurity knowledge.

Potential sources:

- MITRE ATT&CK
- Forensic documentation
- Investigation procedures
- Security documentation
- Detection references

## Tasks

- Evaluate deterministic lookup first.
- Define knowledge sources.
- Build ingestion pipeline if needed.
- Build retrieval.
- Add citations.
- Evaluate retrieval quality.

## Definition of Done

RAG provides useful context that cannot be obtained more reliably from
the structured TRACE-X event store.

RAG must be evaluated for:

- Relevance
- Accuracy
- Citation quality
- Hallucination risk

---

# 16. Phase 13 — Investigator Dashboard

## Goal

Create a professional investigation interface.

## Main views

```text
Cases
Evidence
Artifacts
Events
IOCs
Detections
Incidents
Timeline
Risk
Investigation Graph
AI Assistant
Reports
Audit Log
```

## Dashboard should expose

- Evidence status
- Event counts
- IOC counts
- Detection counts
- Incident counts
- Risk distribution
- Processing failures
- Investigation timeline

## Definition of Done

The UI reflects actual backend functionality.

No visual element may imply functionality that does not exist.

---

# 17. Phase 14 — Reporting & Export

## Goal

Produce professional investigation reports.

## Formats

- PDF
- JSON
- CSV when required

## Report structure

```text
Case Information
Evidence Information
Executive Summary
Key Findings
IOC Summary
Detection Details
Timeline
Risk Assessment
Supporting Evidence
Processing Limitations
Recommendations
Integrity Information
```

## Definition of Done

- Reports contain real data.
- Evidence references are preserved.
- Processing failures are visible.
- Reports are reproducible.
- PDF/JSON outputs pass validation tests.

---

# 18. Phase 15 — Security Hardening

## Goal

Make TRACE-X itself resilient.

## Areas

- Authentication
- Authorization
- RBAC
- Secure file handling
- Input validation
- Path traversal protection
- Upload controls
- Sandboxing
- Resource limits
- Network restrictions
- Secret management
- Audit logging
- API security
- Dependency scanning
- Container security

## Definition of Done

- Threat model exists.
- Security tests exist.
- Critical vulnerabilities are addressed.
- Evidence processing is isolated.
- Unauthorized access is blocked.
- Audit trail works.
- No secrets are committed.

---

# 19. Phase 16 — Testing & Benchmarking

## Goal

Prove that TRACE-X works.

## Test categories

### Unit

Individual functions and components.

### Integration

Component interactions.

### End-to-End

Complete investigator workflows.

### Forensic Fixtures

Known evidence with expected results.

### Controlled Attack Scenarios

Known activities performed in controlled environments.

### Failure Tests

Corrupt, malformed and incomplete evidence.

### Security Tests

Attack the application's boundaries.

---

## Benchmark categories

### Detection

- Precision
- Recall
- False positives
- False negatives

### Performance

- Events/sec
- Processing time
- CPU
- Memory
- Database latency

### Investigation Efficiency

- Manual investigation time
- TRACE-X investigation time
- Time to first useful finding
- Time to generate report

## Definition of Done

Benchmark results are:

- Reproducible
- Documented
- Based on real measurements
- Associated with defined datasets/scenarios

No unsupported metrics are used in presentations or resumes.

---

# 20. Phase 17 — Performance & Scale

## Goal

Optimize TRACE-X based on measured bottlenecks.

Potential areas:

- Parallel parsing
- Background workers
- Database indexing
- Query optimization
- Caching
- Batch processing
- Object storage
- Worker scaling

## Important rule

Do not introduce distributed systems merely because they sound advanced.

Introduce them when benchmarking demonstrates a real need.

## Definition of Done

Performance improvements must include:

```text
Before
 ↓
Change
 ↓
After
 ↓
Measured Improvement
```

---

# 21. Phase 18 — Release / Open Source / SIH

## Goal

Turn TRACE-X into a polished public project.

## Release preparation

- README
- Architecture diagrams
- Installation guide
- Demo instructions
- Security documentation
- Contribution guide
- License
- Changelog
- Release notes
- Screenshots/demo
- Sample cases
- Benchmark results

## Open Source

Potential components:

- Core platform
- Parsers
- Detection rules
- Test fixtures
- Documentation
- Benchmark tools

## SIH

Prepare:

- Problem statement mapping
- Architecture
- Innovation
- Technical feasibility
- Impact
- Demo
- Benchmark evidence
- Deployment story

The SIH submission is a presentation of TRACE-X, not the definition of
the entire project.

---

# 22. Milestone Structure

TRACE-X will use milestones rather than only calendar deadlines.

## M0 — Architecture Ready

```text
TRACESPEC
BRAIN
AGENTS
PIPELINE
ROADMAP
STATUS
Skills
```

All reviewed.

---

## M1 — Foundation Ready

```text
Next.js
FastAPI
PostgreSQL
Redis
Docker
Testing
CI
```

Working locally.

---

## M2 — Evidence Ready

```text
Case
Evidence
Hashing
Integrity
Storage
Audit
```

Working and tested.

---

## M3 — Forensic MVP Ready

```text
Filesystem
Event Logs
Registry
Normalization
Event Store
```

Working and tested.

---

## M4 — Detection MVP Ready

```text
IOC
Rules
Timeline
Risk
```

Working and tested.

---

## M5 — Full MVP Ready

Complete end-to-end investigator workflow.

---

## M6 — Intelligence Ready

```text
Correlation
ML
Graph
```

Stable and evaluated.

---

## M7 — AI Ready

```text
Evidence-grounded AI
RAG
Investigation Copilot
```

Tested for grounding.

---

## M8 — Production-Quality Prototype

```text
Security
Observability
Performance
Benchmarking
Documentation
```

---

## M9 — Public Release

```text
GitHub
Demo
Documentation
Benchmarks
SIH submission
Resume
```

---

# 23. Suggested Development Cadence

The project should not be forced into unrealistic fixed dates.

Instead, work in small implementation cycles.

Each cycle:

```text
Plan
 ↓
Implement
 ↓
Test
 ↓
Review
 ↓
Document
 ↓
Benchmark when applicable
 ↓
Commit
```

A feature should move forward only when its Definition of Done is
satisfied.

---

# 24. AI-Assisted Development Workflow

The primary working relationship is:

```text
YOU
 │
 ├── Product decisions
 ├── Scope
 ├── Architecture approval
 └── Acceptance criteria
 │
 ▼
CLAUDE SONNET
 │
 ├── Architecture
 ├── Planning
 ├── Review
 ├── Security analysis
 └── Debugging
 │
 ▼
ANTIGRAVITY + GEMINI PRO
 │
 ├── Implementation
 ├── File changes
 ├── Testing
 └── Local execution
 │
 ▼
TEST / REVIEW
 │
 ▼
COMMIT
```

Opus is not required for the normal workflow.

---

# 25. Project Constraints

Primary development environment:

```text
MacBook
```

Initial budget constraint:

```text
Maximum approximately ₹1,000
```

The architecture should prefer:

- Open-source
- Local development
- Local ML
- Local storage
- Free tooling

Paid resources should only be introduced when they provide a clear
technical benefit.

Money should not unnecessarily constrain technical ambition.

---

# 26. Roadmap Governance

The roadmap is a living document.

A roadmap item may be:

```text
Planned
In Progress
Completed
Blocked
Postponed
Cancelled
```

Changes must reflect the current project reality.

A feature may move between phases when architecture, testing or
benchmarking shows that the original ordering is no longer optimal.

---

# 27. Long-Term Target

The long-term target is not simply:

> "Complete SIH1744."

The target is:

> Build a technically serious, secure, measurable and open-source
> digital-forensics and cyber-triage platform that demonstrates strong
> software engineering, cybersecurity, ML and AI-assisted engineering
> capability.

SIH is one application of the platform.

The resume value should come from the engineering quality, measurable
results and depth of the project.

---

# 28. Current State

Current phase:

**Phase 9 — ML / Anomaly Detection (Complete)**

Completed:

- Phase 1: Core Architecture, Domain Models, Persistence
- Phase 2: API, Evidence Management, Security Boundaries
- Phase 3: Artifact Extraction (MVP Parsers, Sandbox)
- Phase 4: Event Store & Normalization
- Phase 5: Detection Engine, IOC, Risk Scoring
- Phase 6: Timeline, Audit, Deterministic Risk
- Phase 7: MVP Integration, Frontend UI, CORS, Processing Pipeline
- Phase 8: Correlation Engine
- Phase 9: ML / Anomaly Detection

Next:

- Phase 10: Investigation Graph (Not Started)