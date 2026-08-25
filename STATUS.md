# TRACE-X Project Status

**Version:** 0.1  
**Last Updated:** 2026-08-26  
**Current Phase:** Phase 0 — Research & Architecture  
**Overall Status:** Architecture / Pre-Development

---

# 1. Current Project State

TRACE-X is currently in the **pre-development architecture phase**.

The project repository has been initialized and the core project
documentation is being established before application development begins.

No production application code has been implemented yet.

---

# 2. Project Health

| Area | Status | Notes |
|---|---|---|
| Repository | ✅ Complete | Git repository initialized |
| Project structure | ✅ Complete | Initial documentation structure created |
| Technical specification | ✅ Complete | TRACESPEC v0.2 |
| Project brain | ✅ Complete | BRAIN.md created |
| Agent instructions | ✅ Complete | AGENTS.md created |
| Processing pipeline | ✅ Complete | PIPELINE.md created |
| Development roadmap | ✅ Complete | ROADMAP.md created |
| Status tracking | 🟡 In Progress | STATUS.md being established |
| Agent skills | ⬜ Not Started | Will be created next |
| Architecture review | 🟡 In Progress | Initial Claude review completed |
| Application foundation | ⬜ Not Started | Not yet implemented |
| Backend | ⬜ Not Started | Not yet implemented |
| Frontend | ⬜ Not Started | Not yet implemented |
| Database | ⬜ Not Started | Not yet implemented |
| Forensic engine | ⬜ Not Started | Not yet implemented |
| Detection engine | ⬜ Not Started | Not yet implemented |
| ML engine | ⬜ Not Started | Not yet implemented |
| RAG | ⬜ Not Started | Not yet implemented |
| AI assistant | ⬜ Not Started | Not yet implemented |
| Testing infrastructure | ⬜ Not Started | Not yet implemented |
| CI/CD | ⬜ Not Started | Not yet implemented |
| Benchmarking | ⬜ Not Started | Not yet implemented |
| Deployment | ⬜ Not Started | Local-first development |

---

# 3. Completed

## Project Initialization

- [x] TRACE-X repository created
- [x] Git initialized
- [x] Initial directory structure created
- [x] Initial Git commit created

## Project Constitution

- [x] TRACESPEC.md v0.2
- [x] BRAIN.md
- [x] AGENTS.md
- [x] PIPELINE.md
- [x] ROADMAP.md

## Architecture Decisions Established

- [x] Evidence-first philosophy
- [x] Automation-before-AI principle
- [x] Raw evidence treated as untrusted
- [x] Three-zone trust architecture
- [x] Evidence provenance requirement
- [x] Evidence immutability requirement
- [x] Partial-processing semantics
- [x] MVP scope defined
- [x] Advanced features separated from MVP
- [x] Benchmarking requirements defined
- [x] AI grounding requirement defined

---

# 4. In Progress

## Project Constitution

- [~] STATUS.md
- [ ] Initial TRACE-X agent skills
- [ ] Final architecture validation

## Architecture

- [~] Review TRACESPEC
- [ ] Finalize concrete relational schema
- [ ] Finalize evidence isolation mechanism
- [ ] Finalize sandbox implementation strategy
- [ ] Finalize parser interface
- [ ] Finalize Event schema
- [ ] Finalize API boundaries

---

# 5. Next Tasks

Priority order:

### P0 — Required Before Coding

- [ ] Complete STATUS.md
- [ ] Create initial agent skills
- [ ] Review project documentation as a complete system
- [ ] Finalize the core Event schema
- [ ] Finalize Case/Evidence/Artifact relationships
- [ ] Finalize sandbox strategy
- [ ] Finalize evidence storage strategy
- [ ] Final architecture review

### P1 — Foundation

After architecture approval:

- [ ] Initialize Next.js frontend
- [ ] Initialize FastAPI backend
- [ ] Add PostgreSQL
- [ ] Add Redis
- [ ] Add Docker Compose
- [ ] Add environment configuration
- [ ] Add testing infrastructure
- [ ] Add basic CI
- [ ] Verify frontend → backend → database

---

# 6. Current MVP Scope

The MVP currently includes:

## Evidence

- [ ] Case management
- [ ] Evidence ingestion
- [ ] SHA-256 hashing
- [ ] Evidence integrity
- [ ] Sandboxed processing

## Artifact Extraction

- [ ] Filesystem metadata
- [ ] Windows Event Logs
- [ ] Windows Registry

## Analysis

- [ ] Event normalization
- [ ] PostgreSQL event store
- [ ] Deterministic IOC detection
- [ ] Versioned rule engine
- [ ] Timeline
- [ ] Basic explainable risk scoring

## Reporting

- [ ] JSON report
- [ ] PDF report

## Security

- [ ] Basic authentication
- [ ] Investigator role
- [ ] Audit logging
- [ ] Evidence integrity controls

---

# 7. Advanced Features

Not part of the initial MVP:

- [ ] Correlation Engine
- [ ] ML anomaly detection
- [ ] Investigation Graph
- [ ] Evidence-grounded AI Assistant
- [ ] RAG
- [ ] Advanced forensic artifacts
- [ ] Advanced reporting
- [ ] Multi-user RBAC
- [ ] Performance scaling
- [ ] Distributed processing
- [ ] Plugin architecture

These features should only be promoted into active development after
the MVP is stable.

---

# 8. Development Rules

A feature cannot be marked complete only because code exists.

A feature is complete only when:

- [ ] Implementation works
- [ ] Tests exist
- [ ] Tests pass
- [ ] Failure cases are handled
- [ ] Security is reviewed
- [ ] Documentation is updated
- [ ] Provenance requirements are satisfied
- [ ] Acceptance criteria are satisfied
- [ ] Relevant benchmark exists when applicable
- [ ] STATUS.md is updated

---

# 9. Current Architecture Status

```text
                    TRACE-X

                        │
                        ▼

               UNTRUSTED ZONE
                        │
              Evidence Processing
                        │
                        ▼
             Sandboxed Extraction
                        │
                        ▼

                 TRUSTED ZONE
                        │
                  Normalization
                        │
                        ▼
                   Event Store
                        │
             ┌──────────┼──────────┐
             ▼          ▼          ▼
            IOC       Rules       ML*
             │          │          │
             └──────────┼──────────┘
                        ▼
                 Correlation*
                        │
                  ┌─────┴─────┐
                  ▼           ▼
               Timeline      Risk
                  │           │
                  └─────┬─────┘
                        ▼

             INVESTIGATOR ZONE
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
      Dashboard       AI*          Reports
```

`*` = Advanced / future stage

---

# 10. Known Open Decisions

These decisions must be finalized before the relevant implementation
begins.

## Evidence Storage

Question:

How will the original evidence be stored and protected from modification?

Status:

**Open**

---

## Sandbox Architecture

Question:

What exact isolation mechanism will be used for artifact extraction?

Possible approaches:

- Docker isolation
- Dedicated worker containers
- VM-based isolation
- Other controlled execution environments

Status:

**Open**

---

## Event Schema

Question:

What exact fields, types, constraints and indexes will the final Event
model use?

Status:

**Open**

---

## Parser Interface

Question:

What exact contract must every forensic parser implement?

Status:

**Open**

---

## Correlation Algorithm

Question:

What initial deterministic correlation algorithm will be used?

Status:

**Deferred to Advanced phase**

---

## ML Baseline

Question:

What baseline will define anomalous behavior?

Status:

**Deferred to ML phase**

---

## RAG Architecture

Question:

Does RAG provide enough value over deterministic knowledge lookup to
justify its complexity?

Status:

**Deferred until after MVP**

---

# 11. Metrics to Establish Later

No benchmark values have been established yet.

Future measurements should include:

- Events processed per second
- Total processing time
- Memory consumption
- CPU usage
- Database query latency
- Detection precision
- Detection recall
- False-positive rate
- False-negative rate
- Timeline accuracy
- Investigation time
- Report generation time

---

# 12. AI Development Environment

## Claude

Role:

**Principal Architect / Reviewer**

Preferred model:

**Claude Sonnet**

Primary responsibilities:

- Architecture
- Planning
- Security review
- Code review
- Difficult debugging
- Documentation review

Opus is not part of the normal development workflow.

---

## Antigravity

Role:

**Primary Implementation Agent**

Preferred model:

**Gemini 3.1 Pro High**

Primary responsibilities:

- Implementation
- Repository changes
- Terminal execution
- Testing
- Local debugging
- Refactoring
- UI implementation

---

# 13. Current AI Workflow

```text
User
 ↓
Requirement
 ↓
Claude Sonnet
 ↓
Architecture / Plan
 ↓
User Approval
 ↓
Antigravity + Gemini Pro
 ↓
Implementation
 ↓
Tests
 ↓
Claude Review
 ↓
Fixes
 ↓
Git Commit
 ↓
STATUS.md Update
```

No agent should silently make major architectural changes.

---

# 14. Git Milestones

Current commits:

```text
1. Project structure initialized
2. TRACESPEC v0.2
3. BRAIN.md
4. AGENTS.md
5. PIPELINE.md
6. ROADMAP.md
```

Next expected milestone:

```text
7. STATUS.md
```

Future commits should use meaningful messages.

Examples:

```text
feat: add evidence hashing
feat: add event normalization
fix: handle malformed evtx input
test: add registry parser fixtures
docs: update forensic pipeline
refactor: isolate parser execution
```

---

# 15. Current Definition of "Ready to Code"

TRACE-X is ready to begin application implementation when:

- [x] TRACESPEC exists
- [x] BRAIN exists
- [x] AGENTS exists
- [x] PIPELINE exists
- [x] ROADMAP exists
- [x] STATUS exists
- [ ] Initial Skills exist
- [ ] Architecture review is complete
- [ ] Core Event schema is finalized
- [ ] Evidence isolation approach is finalized
- [ ] Parser contract is finalized
- [ ] Initial implementation task is approved

Until these conditions are satisfied:

> Do not begin uncontrolled application development.

---

# 16. Immediate Next Step

After STATUS.md is committed:

```text
Create TRACE-X Skills
        ↓
Architecture consistency review
        ↓
Finalize data model
        ↓
Finalize foundation architecture
        ↓
Begin Phase 1
```

---

# 17. Status Legend

```text
✅ Complete
~  In Progress
⬜ Not Started
⛔ Blocked
⏸️ Postponed
```

---

# 18. Status Governance

STATUS.md is the current representation of the project's actual state.

It must be updated when:

- A feature starts
- A feature completes
- A feature is blocked
- A milestone is completed
- Architecture changes
- A major decision is made
- A benchmark is completed

Do not leave STATUS.md describing outdated project state.

---

# 19. Current Summary

```text
Project:
TRACE-X

Purpose:
Evidence-centric digital forensics and cyber triage

Current Phase:
Phase 0 — Research & Architecture

Specification:
TRACESPEC v0.2

Application Code:
Not Started

AI Development:
Claude Sonnet + Antigravity Gemini Pro

Development Environment:
MacBook

Strategy:
Local-first / open-source-first

Primary Immediate Goal:
Complete the project constitution and architecture
before implementation.
```