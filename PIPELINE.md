# TRACE-X Processing Pipeline

**Version:** 0.1  
**Purpose:** Define how evidence and analysis data move through TRACE-X  
**Last Updated:** 2026-08-26

---

# 1. Pipeline Overview

TRACE-X converts raw forensic evidence into structured, explainable
investigation findings.

The high-level flow is:

```text
Evidence
   ↓
Validation
   ↓
Integrity Verification
   ↓
Sandboxed Ingestion
   ↓
Artifact Extraction
   ↓
Normalization
   ↓
Event Store
   │
   ├──────────────→ IOC Detection
   │
   ├──────────────→ Rule Detection
   │
   └──────────────→ Anomaly Detection
                           │
                           ↓
                    Correlation
                           ↓
                 ┌─────────┴─────────┐
                 ↓                   ↓
              Timeline           Risk Engine
                 │                   │
                 └─────────┬─────────┘
                           ↓
                     Investigation
                           │
              ┌────────────┼────────────┐
              ↓            ↓            ↓
          Dashboard      AI/RAG       Reports
```

---

# 2. Trust Zones

TRACE-X has three major processing zones.

```text
┌─────────────────────────────────────────────┐
│              UNTRUSTED ZONE                 │
│                                             │
│ Evidence → Validation → Hash → Extraction │
│                                             │
│ Input must be treated as hostile.           │
└──────────────────────┬──────────────────────┘
                       │
                       │ Structured validated output
                       ▼
┌─────────────────────────────────────────────┐
│               TRUSTED ZONE                  │
│                                             │
│ Normalization → Event Store                 │
│                                             │
│       ┌────────┬────────┬────────┐          │
│       ↓        ↓        ↓        │          │
│      IOC     Rules     ML        │          │
│       └────────┴────────┴────────┘          │
│                    ↓                        │
│                Correlation                  │
│                    ↓                        │
│             Timeline / Risk                │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│          INVESTIGATOR-FACING ZONE            │
│                                             │
│ Dashboard / Graph / AI / Reports            │
└─────────────────────────────────────────────┘
```

Raw evidence should not directly enter the trusted or
investigator-facing zones.

---

# 3. Stage 1 — Case Creation

The investigator begins by creating a Case.

```text
User
 ↓
Create Case
 ↓
case_id
 ↓
Case Record
```

A Case becomes the top-level container for the investigation.

Example:

```text
CASE-2026-001
Title: Suspicious Workstation Activity
Status: Open
Created By: Investigator
```

---

# 4. Stage 2 — Evidence Ingestion

The investigator adds evidence to the case.

```text
Case
 ↓
Evidence Upload
 ↓
Input Validation
 ↓
Evidence Record
```

The system records metadata such as:

- evidence_id
- case_id
- name
- type
- size
- source
- acquisition metadata
- ingestion timestamp

At this stage the original evidence is still considered untrusted.

---

# 5. Stage 3 — Evidence Integrity

Before analysis:

```text
Evidence
    ↓
SHA-256
    ↓
Integrity Record
```

The system stores the original evidence hash.

The original evidence must be treated as immutable.

Integrity state may include:

```text
UNKNOWN
VALID
FAILED
```

A failed integrity check must become visible to the investigator.

---

# 6. Stage 4 — Sandboxed Ingestion

Evidence is transferred into a controlled processing environment.

```text
Original Evidence
       ↓
Controlled Access
       ↓
Sandbox
```

The sandbox should enforce:

- Restricted filesystem access
- Least privilege
- CPU limits
- Memory limits
- Execution timeout
- Restricted/disabled network access
- Process/container isolation

Evidence content must never be interpreted as instructions.

---

# 7. Stage 5 — Artifact Extraction

The forensic extraction engine identifies useful artifacts.

For MVP:

```text
Evidence
   │
   ├── Filesystem Metadata
   │
   ├── Windows Event Logs
   │
   └── Windows Registry
```

Each extractor generates structured artifacts.

Example:

```text
Evidence
   ↓
Registry Hive
   ↓
Registry Artifact
```

or:

```text
Evidence
   ↓
EVTX File
   ↓
Event Log Artifact
```

Every Artifact must retain:

- evidence_id
- artifact_id
- artifact_type
- source_location
- parser_name
- parser_version
- extraction_status
- provenance

---

# 8. Stage 6 — Failure Handling

Artifact extraction is not assumed to be perfect.

A parser may produce:

```text
SUCCESS
PARTIAL
FAILED
SKIPPED
```

Example:

```text
Registry Hive A → SUCCESS
Registry Hive B → PARTIAL
EVTX File A     → FAILED
EVTX File B     → SUCCESS
```

The case itself may still continue processing.

Important rule:

> Missing analysis must never be interpreted as absence of evidence.

The final investigation must expose important processing gaps.

---

# 9. Stage 7 — Normalization

Different artifact formats are converted into the common TRACE-X Event
model.

Example:

```text
Registry Artifact
       ↓
   Normalizer
       ↓
      Event
```

```text
EVTX Artifact
       ↓
   Normalizer
       ↓
      Event
```

```text
Filesystem Artifact
       ↓
   Normalizer
       ↓
      Event
```

All downstream analytical components work primarily with the normalized
Event model.

---

# 10. Stage 8 — Event Store

Normalized events are stored in the event store.

Initial technology:

```text
PostgreSQL
```

Conceptually:

```text
Artifact
   ↓
Normalization
   ↓
Event
   ↓
PostgreSQL
```

The event store is the primary trusted source for downstream analysis.

Events must remain linked to:

```text
Event
 ↓
Artifact
 ↓
Evidence
 ↓
Case
```

---

# 11. Stage 9 — Parallel Detection

Once normalized events are available, independent detection operations
can run in parallel.

```text
                    Event Store
                         │
          ┌──────────────┼──────────────┐
          ↓              ↓              ↓
     IOC Engine      Rule Engine    ML Engine
          │              │              │
          ↓              ↓              ↓
       IOC Result    Rule Result    Anomaly Result
          │              │              │
          └──────────────┼──────────────┘
                         ↓
                     Detections
```

## 11.1 IOC Detection

Detect deterministic indicators.

Examples:

```text
IP
Domain
URL
Hash
Filename
Registry indicator
```

Output:

```text
IOC
+
supporting Event/Artifact
```

---

## 11.2 Rule Detection

Rules identify known patterns.

Example:

```text
PowerShell
     +
Suspicious command
     +
Network connection
     ↓
Detection
```

Every detection must preserve:

- rule_id
- rule_version
- supporting events
- evidence references
- severity
- confidence

---

## 11.3 Anomaly Detection

Anomaly detection is an Advanced feature.

```text
Event Data
    ↓
Feature Extraction
    ↓
Baseline
    ↓
Anomaly Model
    ↓
Anomaly Score
```

The baseline strategy must be defined before this stage becomes part of
the production pipeline.

---

# 12. Stage 10 — Correlation

Correlation combines related Events, IOCs and Detections.

Initial approaches may include:

```text
Shared entity
+
Time window
+
Process relationship
+
File relationship
+
Network relationship
+
Evidence provenance
```

Example:

```text
Event A: PowerShell
      ↓
Event B: suspicious.exe created
      ↓
Event C: external IP contacted
      ↓
Event D: registry persistence
```

The correlation layer may create:

```text
Incident #INC-001
```

with relationships to all supporting Events and Detections.

Correlation is an Advanced feature for the MVP.

---

# 13. Stage 11 — Timeline Construction

The Timeline Engine consumes Events and optionally correlated activity.

```text
Event Store
    ↓
Timeline Engine
    ↓
Chronological Events
```

Example:

```text
10:21:05  User login
10:24:12  PowerShell execution
10:25:31  Suspicious file created
10:26:10  Network connection
10:27:14  Registry modification
```

Timeline filtering may include:

- Time range
- Event type
- Source
- Severity
- User
- Process
- Incident
- IOC

---

# 14. Stage 12 — Risk Scoring

Risk scoring consumes detection and contextual signals.

```text
IOC
 │
Rule
 │
Anomaly
 │
Correlation
 │
Context
 ↓
Risk Engine
 ↓
Risk Score
```

Example:

```text
IOC evidence          +25
Rule detection        +20
Persistence           +20
Network anomaly       +15
Correlation           +20
---------------------------
Risk Score             100
```

The final formula must be experimentally validated.

Every score should contain an explanation of contributing factors.

---

# 15. Stage 13 — Incident Formation

The Investigation system combines:

```text
Events
+
IOCs
+
Detections
+
Correlation
+
Risk
```

into investigator-facing incidents.

Example:

```text
INCIDENT-001

Severity: HIGH
Confidence: 91%

Supporting:
- EV-1021
- EV-1043
- REG-029
- NET-551
```

An Incident must preserve its supporting provenance.

---

# 16. Stage 14 — Investigation Layer

The investigator interacts with processed information rather than raw
untrusted content.

```text
Processed Investigation
          │
    ┌─────┼─────┐
    ↓     ↓     ↓
Timeline Graph  AI
```

The investigator should be able to:

- Inspect findings.
- Navigate timelines.
- Inspect IOCs.
- Inspect events.
- Trace findings back to evidence.
- Understand risk factors.
- Ask investigation questions.

---

# 17. Stage 15 — Investigation Graph

Advanced feature.

The graph may represent:

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

The graph is derived from the trusted event/entity model.

It must not independently invent relationships.

Every important edge should be explainable by underlying evidence.

---

# 18. Stage 16 — AI Investigation Assistant

Advanced feature.

The AI does not directly analyze arbitrary raw evidence.

Instead:

```text
Investigator Question
        ↓
Query / Retrieval Layer
        ↓
Structured TRACE-X Data
        ↓
Optional Knowledge Retrieval
        ↓
LLM
        ↓
Grounding / Validation
        ↓
Response
```

Example:

```text
Question:
Why is Incident #001 high risk?

        ↓

Retrieve:
Events
Detections
IOCs
Risk factors
Evidence references

        ↓

LLM

        ↓

Evidence-backed answer
```

The assistant must distinguish:

```text
Observed Evidence
Inference
Recommendation
```

---

# 19. Stage 17 — RAG Knowledge Layer

RAG is an Advanced feature.

The knowledge layer may contain:

- MITRE ATT&CK
- Forensic documentation
- Security references
- Detection documentation
- Investigation guidance

The RAG layer should answer knowledge questions such as:

> What technique does this behavior resemble?

It should not replace the structured forensic event store.

---

# 20. Stage 18 — Reporting

The Report Engine consumes trusted investigation data.

```text
Case
Events
IOCs
Detections
Incidents
Timeline
Risk
Evidence Metadata
Processing Status
     ↓
Report Engine
     ↓
PDF / JSON
```

Reports must include limitations when processing was incomplete.

Reports must preserve source references.

---

# 21. Complete Data Lineage

Every important result should follow this chain:

```text
CASE
  ↓
EVIDENCE
  ↓
ARTIFACT
  ↓
EVENT
  ↓
IOC / DETECTION
  ↓
INCIDENT
  ↓
TIMELINE / RISK
  ↓
REPORT / AI RESPONSE
```

This is a fundamental TRACE-X principle.

If a final claim cannot be traced backward through this chain, it should
not be presented as an evidence-backed conclusion.

---

# 22. Example End-to-End Scenario

Suppose a controlled test machine generates:

```text
PowerShell execution
Suspicious file creation
External network connection
Registry persistence
```

TRACE-X processes it as:

```text
Evidence
 ↓
Artifacts
 ↓
Events
 ↓
IOC Detection
 ↓
Rule Detection
 ↓
Correlation
 ↓
Incident
 ↓
Timeline
 ↓
Risk
 ↓
Investigator
 ↓
Report
```

The investigator sees:

```text
INCIDENT-001
Severity: HIGH

10:24
PowerShell executed

10:25
Suspicious executable created

10:26
External network connection

10:27
Persistence-related Registry modification
```

The investigator can then inspect the supporting evidence behind each
event.

---

# 23. Processing State Model

A Case and its pipeline stages should expose processing state.

Suggested states:

```text
CREATED
QUEUED
PROCESSING
PARTIAL
COMPLETED
FAILED
CANCELLED
```

An individual artifact may use:

```text
PENDING
PROCESSING
SUCCESS
PARTIAL
FAILED
SKIPPED
```

State transitions must be explicit.

---

# 24. Important Pipeline Rules

## Rule 1

Raw evidence is untrusted.

## Rule 2

Original evidence is immutable.

## Rule 3

Only validated structured data crosses the trust boundary.

## Rule 4

Every important derived object preserves provenance.

## Rule 5

One parser failure must not automatically destroy the entire case.

## Rule 6

Missing data must be visible.

## Rule 7

Deterministic detection comes before ML.

## Rule 8

ML is a signal, not proof.

## Rule 9

AI is an explanation/investigation layer, not the source of truth.

## Rule 10

Reports must reflect processing limitations.

---

# 25. MVP Pipeline

The actual MVP pipeline is deliberately smaller:

```text
Case
 ↓
Evidence
 ↓
SHA-256
 ↓
Sandbox
 ↓
Filesystem Metadata
Windows Event Logs
Windows Registry
 ↓
Normalization
 ↓
Event Store
 ↓
IOC Detection
 ↓
Rule Engine
 ↓
Timeline
 ↓
Basic Risk Score
 ↓
JSON / PDF
```

The MVP should be fully functional before Advanced features are added.

---

# 26. Advanced Pipeline

After MVP:

```text
MVP Pipeline
      ↓
Correlation Engine
      ↓
Anomaly Detection
      ↓
Investigation Graph
      ↓
Evidence-grounded AI
      ↓
RAG
      ↓
Advanced Reporting
      ↓
Performance / Scale
```

---

# 27. Pipeline Evolution

The pipeline is expected to evolve.

When introducing a new stage:

1. Define its input.
2. Define its output.
3. Define its trust boundary.
4. Define failure behavior.
5. Define provenance requirements.
6. Define tests.
7. Define performance expectations.
8. Update this document.

No new stage should be added merely because it sounds technically
impressive.

---

# 28. Current Pipeline Status

Current state:

**Phase 9 ML/Anomaly Detection is complete.**

Current next steps:

```text
Phase 10: Investigation Graph
```