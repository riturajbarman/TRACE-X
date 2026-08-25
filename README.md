# TRACE-X

## Intelligent Digital Forensics & Cyber Triage Platform

TRACE-X is an evidence-first digital forensics and cyber triage platform designed to help investigators understand suspicious activity on computers and digital systems.

The platform ingests forensic evidence, extracts artifacts, normalizes events, identifies indicators of compromise (IOCs), detects suspicious behavior, correlates related activity, builds investigation timelines, calculates explainable risk scores, and generates investigation reports.

> **Evidence → Events → Detection → Correlation → Timeline → Risk → Investigation Report**

---

# Why TRACE-X?

When a computer is suspected to be compromised, investigators may need to examine thousands or millions of digital artifacts.

Relevant information can be scattered across:

- Filesystems
- Windows Event Logs
- Windows Registry
- Browser artifacts
- Prefetch
- LNK files
- USB artifacts
- Network activity
- Processes
- Authentication events
- File metadata

Manually connecting these clues can take significant time.

TRACE-X aims to reduce that effort by turning large amounts of forensic evidence into an understandable investigation story.

---

# Real-World Example

Suppose an employee's laptop is suspected of being compromised.

An investigation may reveal:

```text
10:21 AM
User logged in
        ↓
10:24 AM
PowerShell executed
        ↓
10:25 AM
Suspicious executable created
        ↓
10:26 AM
External IP contacted
        ↓
10:27 AM
Registry persistence modified
        ↓
10:29 AM
Sensitive files accessed
```

TRACE-X correlates these events and may produce:

```text
Risk Score: 91 / 100

Severity: CRITICAL
```

The system should also explain why:

```text
+25 Suspicious network connection
+20 Suspicious executable
+18 PowerShell activity
+15 Persistence mechanism
+13 Related suspicious events
```

The investigator can then inspect the original evidence supporting each finding.

---

# Core Pipeline

TRACE-X follows an evidence-first processing pipeline:

```text
                    ┌─────────────────────┐
                    │     Investigator    │
                    │      Dashboard      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Evidence Ingestion  │
                    │                     │
                    │ RAW / E01 / ZIP /   │
                    │ directories / logs  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Artifact Extraction │
                    │                     │
                    │ Files               │
                    │ Registry            │
                    │ Event Logs          │
                    │ Browser             │
                    │ Network             │
                    │ Processes           │
                    │ USB                 │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Event Normalization │
                    │                     │
                    │ Common Event Model  │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┼──────────────┐
                 ▼             ▼              ▼
          ┌────────────┐ ┌────────────┐ ┌────────────┐
          │ IOC Engine │ │ Rule Engine│ │ ML Engine  │
          └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
                │              │              │
                └──────────────┼──────────────┘
                               ▼
                    ┌─────────────────────┐
                    │ Correlation Engine  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Risk Scoring Engine │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┴─────────────┐
                 ▼                           ▼
        ┌──────────────────┐       ┌──────────────────┐
        │ Investigation UI │       │ Report Generator │
        │                  │       │                  │
        │ Timeline         │       │ PDF              │
        │ IOC Explorer     │       │ JSON             │
        │ Evidence         │       │ CSV              │
        │ Graph            │       │ Findings         │
        └──────────────────┘       └──────────────────┘
```

---

# Architecture Principles

TRACE-X is built around several core principles.

### 1. Evidence First

Original evidence must be preserved and treated as untrusted input.

### 2. Automation Second

Deterministic extraction, normalization, detection and correlation should provide the foundation.

### 3. AI Last

AI should assist investigators rather than replace deterministic forensic analysis.

### 4. Explainability

Important findings must be traceable to the evidence and reasoning that produced them.

### 5. Provenance

Derived artifacts, events, detections and incidents must maintain a connection to their source evidence.

### 6. Security

Evidence processing must be isolated from trusted application components.

### 7. Reproducibility

Analysis should record relevant parser, rule, schema and model versions.

---

# Trust Model

TRACE-X conceptually separates the system into trust zones:

```text
UNTRUSTED
    │
    │ Evidence
    ▼
Validation
    │
    ▼
Hashing
    │
    ▼
Sandboxed Extraction
    │
    ▼
TRUSTED
    │
    ├── Normalization
    ├── Event Store
    ├── Detection
    ├── Correlation
    ├── Timeline
    └── Risk Analysis
    │
    ▼
INVESTIGATOR
    │
    ├── Dashboard
    ├── Investigation Tools
    ├── AI Assistance
    └── Reports
```

---

# Main Capabilities

## Evidence Ingestion

TRACE-X is designed to support forensic evidence such as:

- RAW / DD images
- E01 images
- ZIP evidence packages
- Evidence directories
- Log collections
- Other approved forensic formats

Each evidence item should have an integrity record.

Example:

```text
Evidence ID
SHA-256
Size
Source
Acquisition metadata
Ingestion timestamp
Integrity status
```

---

# Artifact Extraction

The platform is designed around independent forensic parsers.

Potential artifact sources include:

```text
Filesystem
Windows Registry
Windows Event Logs
Browser artifacts
Prefetch
LNK files
USB history
Network artifacts
Process information
Authentication events
```

Each parser should preserve provenance and report its processing status.

---

# Common Event Model

Different artifact sources produce different data.

TRACE-X normalizes relevant observations into a common Event model.

Conceptually:

```text
Event
├── timestamp
├── source
├── event_type
├── user
├── host
├── process
├── file
├── ip
├── domain
├── hash
├── command
├── description
├── severity
├── confidence
└── evidence_id
```

The exact schema is defined by the project specification.

---

# IOC Detection

TRACE-X can identify indicators of compromise such as:

```text
IP addresses
Domains
URLs
File hashes
Suspicious filenames
File paths
Processes
Registry keys
Commands
```

IOC findings should remain linked to their original evidence.

---

# Detection Engine

Detection should primarily use deterministic and explainable mechanisms.

Example:

```text
PowerShell execution
        +
Suspicious command
        +
Network connection
        +
Persistence modification
        ↓
Suspicious activity pattern
```

The system should explain which observations caused a rule to trigger.

---

# Behavioral Anomaly Detection

Machine learning can be used to identify unusual behavior.

Potential features include:

```text
Process frequency
Network connection frequency
Rare commands
Unusual execution times
New executable files
PowerShell activity
Registry modifications
Authentication anomalies
```

Anomaly detection should indicate unusual behavior rather than automatically declaring something malicious.

Example:

```text
Anomaly Score: 0.91

Observed reasons:

- Rare process
- Unusual execution time
- Unknown executable
- External network connection
```

---

# Correlation Engine

The correlation engine connects related observations.

Example:

```text
PowerShell
     ↓
Suspicious command
     ↓
File creation
     ↓
Network connection
     ↓
Persistence
```

These related events may form a single investigation finding or incident.

---

# Risk Scoring

TRACE-X can combine multiple signals into an explainable risk score.

Example:

```text
Risk Score: 87 / 100

CRITICAL

Signals:

+25 Suspicious IOC
+20 PowerShell anomaly
+18 Persistence mechanism
+14 External communication
+10 Credential-related activity
```

The scoring model should remain configurable and explainable.

---

# Investigation Timeline

One of TRACE-X's central features is an interactive investigation timeline.

Example:

```text
08:31:02
User login

08:32:15
PowerShell executed

08:32:18
Encoded command detected

08:32:21
External IP contacted

08:32:25
Suspicious executable created

08:33:04
Persistence modified
```

This allows investigators to understand the sequence of activity rather than reviewing isolated events.

---

# Evidence Graph

TRACE-X can represent relationships between entities.

Example:

```text
USER
 │
 ├── PROCESS
 │      │
 │      ├── FILE
 │      │
 │      └── NETWORK
 │              │
 │              └── IP
 │
 └── REGISTRY
```

This can help investigators explore relationships between:

- Users
- Processes
- Files
- Hashes
- Domains
- IP addresses
- Registry keys
- Events
- Incidents

---

# Investigation Copilot

AI may assist investigators with questions such as:

```text
Why is this incident considered critical?
```

or:

```text
What events happened before the suspicious connection?
```

AI responses must be grounded in TRACE-X evidence and structured analysis.

AI must not invent forensic findings.

Where possible, AI-generated explanations should link back to:

```text
Evidence
Artifact
Event
Detection
Incident
```

---

# Attack Story

TRACE-X may summarize correlated activity into an understandable attack story.

Example:

```text
Initial Access
      ↓
Execution
      ↓
Persistence
      ↓
Discovery
      ↓
Credential Access
      ↓
Command & Control
```

Where appropriate, behaviors can be mapped to MITRE ATT&CK techniques.

The mapping must be evidence-backed.

---

# Reporting

TRACE-X should generate investigation reports containing:

```text
Executive Summary

Evidence Information

Evidence Integrity

System Information

Key Findings

IOC Summary

Suspicious Activities

Investigation Timeline

Risk Assessment

Detection Details

Recommendations

Appendix
```

Supported output formats may include:

```text
PDF
JSON
CSV
```

---

# Technology Stack

The planned stack is:

| Layer | Technology |
|---|---|
| Frontend | Next.js + TypeScript |
| UI | Tailwind CSS + shadcn/ui |
| Charts | Recharts |
| Timeline | Custom / timeline library |
| Graph | React Flow |
| Backend | FastAPI |
| Language | Python |
| Database | PostgreSQL |
| Queue / Cache | Redis |
| Workers | Celery or equivalent |
| Object Storage | MinIO |
| Machine Learning | scikit-learn |
| PDF Reports | ReportLab |
| Containers | Docker |
| Testing | Pytest + Playwright |
| API | OpenAPI |

Technology choices may change when justified by the architecture and project requirements.

---

# Repository Structure

The project constitution currently contains:

```text
TRACE-X/
├── BRAIN.md
├── TRACESPEC.md
├── AGENTS.md
├── PIPELINE.md
├── ROADMAP.md
├── STATUS.md
├── README.md
│
└── .agents/
    └── skills/
        ├── tracex-architecture/
        ├── tracex-forensics/
        ├── tracex-security/
        ├── tracex-testing/
        ├── tracex-detection/
        └── tracex-code-review/
```

As implementation begins, application directories will be added according to the approved architecture.

---

# Development Philosophy

TRACE-X is intentionally built in small, testable vertical slices.

The preferred workflow is:

```text
PLAN
  ↓
IMPLEMENT
  ↓
TEST
  ↓
REVIEW
  ↓
FIX
  ↓
COMMIT
```

AI coding agents should not be given uncontrolled permission to redesign the entire system.

Changes should respect:

- BRAIN.md
- TRACESPEC.md
- AGENTS.md
- PIPELINE.md
- ROADMAP.md
- STATUS.md
- `.agents/skills/`

---

# AI-Assisted Development

TRACE-X uses AI coding agents as engineering assistants.

AI may help with:

- Architecture analysis
- Implementation
- Testing
- Code review
- Documentation
- Debugging
- Refactoring
- UI development
- Investigation assistance

However:

> AI-generated code and AI-generated forensic conclusions are not automatically trusted.

All important behavior must be reviewed and tested.

---

# Development Stages

The planned development progression is:

## Stage 1 — Foundation

```text
Repository
Architecture
Docker
FastAPI
Next.js
PostgreSQL
Authentication
Evidence model
```

## Stage 2 — Forensics

```text
Evidence ingestion
Hashing
File metadata
Event Logs
Registry
Browser artifacts
Prefetch
USB artifacts
```

## Stage 3 — Intelligence

```text
IOC engine
Detection rules
Event normalization
Timeline
Correlation
Risk scoring
```

## Stage 4 — Machine Learning

```text
Feature extraction
Anomaly detection
Anomaly scoring
Explainability
```

## Stage 5 — Investigator Experience

```text
Dashboard
Timeline
Evidence explorer
IOC explorer
Evidence graph
Investigation views
```

## Stage 6 — Reporting

```text
PDF
JSON
CSV
```

## Stage 7 — Hardening

```text
Security testing
Performance testing
Parser testing
Failure handling
Deployment
Documentation
Demo dataset
```

---

# What TRACE-X Is Not

TRACE-X is not intended to:

- Replace professional forensic investigators
- Automatically declare guilt
- Automatically prove criminal activity
- Modify original evidence
- Execute arbitrary evidence content
- Treat AI output as forensic truth
- Hide uncertainty
- Fabricate missing evidence

TRACE-X is an investigation-assistance platform.

---

# Current Status

See:

```text
STATUS.md
```

for the current implementation state.

See:

```text
ROADMAP.md
```

for planned development.

See:

```text
TRACESPEC.md
```

for the detailed technical specification.

See:

```text
PIPELINE.md
```

for the processing pipeline.

See:

```text
AGENTS.md
```

for AI-agent operating rules.

See:

```text
BRAIN.md
```

for project-level architectural reasoning and decisions.

---

# Project Constitution

TRACE-X uses a project-constitution approach to keep AI-assisted development consistent.

The constitution consists of:

```text
BRAIN.md
TRACESPEC.md
AGENTS.md
PIPELINE.md
ROADMAP.md
STATUS.md
.agents/skills/
```

These documents are authoritative for project development.

If implementation conflicts with the project constitution, the conflict must be identified and resolved rather than silently ignored.

---

# Development Status

> 🚧 TRACE-X is currently under active development.

The project is currently focused on establishing the architecture, development rules, forensic processing model, security boundaries, testing strategy, and detection framework before implementing the full investigation platform.

---

# Long-Term Vision

The long-term goal is to make TRACE-X capable of transforming complex digital evidence into an understandable and evidence-backed investigation.

The intended flow is:

```text
Raw Evidence
     ↓
Evidence Integrity
     ↓
Artifact Extraction
     ↓
Event Normalization
     ↓
IOC Detection
     ↓
Behavior Detection
     ↓
Correlation
     ↓
Timeline Reconstruction
     ↓
Risk Assessment
     ↓
Investigator Analysis
     ↓
AI-Assisted Explanation
     ↓
Investigation Report
```

The central principle remains:

> **Preserve the evidence. Extract the facts. Connect the clues. Explain the findings.**