# TRACE-X Technical Specification

**Version:** 0.2  
**Status:** Draft  
**Project:** TRACE-X  
**Last Updated:** 2026-08-26

---

# 1. Product Definition

## 1.1 What is TRACE-X?

TRACE-X is an evidence-centric digital forensics and cyber-triage
platform.

Its purpose is to help investigators turn large amounts of digital
forensic evidence into an understandable, traceable investigation.

TRACE-X will:

1. Ingest forensic evidence.
2. Preserve evidence integrity.
3. Extract forensic artifacts.
4. Normalize artifacts into a common event model.
5. Detect indicators of compromise (IOCs).
6. Apply deterministic detection rules.
7. Support behavioral anomaly detection.
8. Correlate related events.
9. Build investigation timelines.
10. Generate explainable risk scores.
11. Provide evidence-grounded investigation assistance.
12. Generate investigation reports.

TRACE-X is intended to be:

- A serious engineering project.
- A potential SIH solution.
- An open-source/research project.
- A practical learning project for cybersecurity.
- A practical learning project for software engineering.
- A practical learning project for ML and AI-assisted development.

---

# 2. Problem

A compromised computer can contain a huge amount of evidence distributed
across:

- Files
- Windows Event Logs
- Windows Registry
- Browser artifacts
- Process activity
- Network activity
- USB/device activity
- Persistence mechanisms
- File metadata
- Other forensic artifacts

Manually connecting these pieces can be slow and difficult.

TRACE-X aims to reduce the time required for initial cyber triage by
automatically processing evidence, identifying suspicious activity,
correlating related events, and presenting useful findings in an
investigator-friendly form.

The primary problem TRACE-X should help answer is:

> "What happened on this system, when did it happen, what evidence
> supports that conclusion, and how serious is it?"

---

# 3. Target Users

## 3.1 Primary Users

- Digital forensic investigators
- Incident response teams
- Cybersecurity analysts
- SOC/security teams
- Cybercrime investigators
- Security researchers

## 3.2 Secondary Users

- Students learning digital forensics
- Researchers
- Organizations performing internal investigations

---

# 4. Product Goals

TRACE-X prioritizes:

1. Evidence integrity
2. Explainability
3. Automation
4. Investigation speed
5. Traceability
6. Security
7. Reproducibility
8. Modularity
9. Measurable performance

TRACE-X should not merely produce suspiciousness scores.

It should help an investigator understand:

- What happened
- When it happened
- Why it is suspicious
- What evidence supports the finding
- What should be investigated next

---

# 5. System Processing Architecture

TRACE-X is not a strictly linear pipeline.

The system is a directed processing graph in which independent analysis
operations may execute in parallel after normalized events become
available.

The architecture is divided into three trust zones.

---

## 5.1 Untrusted Processing Zone

This zone handles potentially hostile forensic input.

```text
Evidence
   ↓
Validation
   ↓
Hashing
   ↓
Ingestion
   ↓
Sandboxed Artifact Extraction
```

All evidence content must be treated as untrusted.

Potentially attacker-controlled content includes:

- File contents
- Filenames
- File metadata
- Registry values
- Embedded strings
- URLs
- Domains
- Command strings
- Malformed logs
- Timestamps
- Other metadata

Extractor processes must operate with:

- Least privilege
- Restricted filesystem access
- Restricted or disabled network access
- CPU limits
- Memory limits
- Execution timeouts
- Process/container isolation
- Safe error handling
- Validated structured output

Raw evidence must not directly cross into trusted processing components.

---

## 5.2 Trusted Processing Zone

Only schema-validated structured output from artifact extraction enters
this zone.

```text
Normalized Artifacts
        ↓
    Event Store
        │
        ├───────────────┐
        ↓               ↓
   IOC Detection    Rule Detection
        │               │
        └───────┬───────┘
                ↓
       Optional Anomaly Detection
                ↓
         Correlation Engine
                ↓
       ┌────────┴────────┐
       ↓                 ↓
   Timeline          Risk Engine
       │                 │
       └────────┬────────┘
                ↓
          Investigation
```

Independent analysis stages should be parallelizable where practical.

---

## 5.3 Investigator-Facing Zone

The investigator-facing components consume structured, validated
investigation data.

```text
Timeline
   │
Incident / Risk Information
   │
   ├── Investigation Graph
   ├── AI Investigation Assistant
   └── Report Generator
```

Raw untrusted evidence must not be passed directly to the AI assistant
or report generator.

All data entering investigator-facing components must be validated,
escaped and represented using approved domain models.

---

# 6. Core Components

## 6.1 Evidence Management

Responsible for:

- Case creation
- Evidence ingestion
- Evidence metadata
- SHA-256 hashing
- Evidence integrity
- Evidence provenance
- Processing status
- Evidence access control

### Evidence Immutability

Original evidence must never be modified by normal TRACE-X processing.

The system must:

1. Store original evidence separately from working data.
2. Record a SHA-256 hash at ingestion.
3. Treat the original evidence as read-only.
4. Perform hash verification when integrity validation is required.
5. Perform extraction and transformation against controlled working
   copies or read-only mounts.
6. Record provenance for derived artifacts.
7. Record integrity failures as explicit investigation events.

The exact storage/isolation mechanism will be finalized during
architecture implementation.

---

## 6.2 Artifact Extraction

Initial artifact categories considered for the full project:

- Filesystem
- Windows Event Logs
- Windows Registry
- Browser history/artifacts
- Prefetch
- LNK files
- USB/device artifacts
- Network artifacts
- Scheduled Tasks
- Services

However, the MVP intentionally limits extraction to:

1. Filesystem metadata
2. Windows Event Logs
3. Windows Registry

Additional artifact types are added only after the core architecture is
stable.

Each parser must expose:

- Parser name
- Parser version
- Input type
- Extraction status
- Provenance
- Error information
- Structured output

---

## 6.3 Normalization Engine

All extracted forensic data should be converted into a common event
representation.

The normalized event model allows downstream systems to operate
independently of individual artifact formats.

Potential event fields include:

- timestamp
- timestamp_precision
- source
- event_type
- user
- host
- process
- file
- ip
- domain
- hash
- command
- description
- severity
- confidence
- evidence_id
- artifact_id

Optional fields must be explicitly distinguishable from missing or
unknown values.

The finalized schema will be treated as a versioned domain contract.

---

## 6.3.1 Core Data Model

The following entities form the core domain model of TRACE-X.

### Case

Represents an investigation.

Core fields:

- case_id
- title
- description
- status
- created_at
- updated_at
- created_by

A Case contains one or more Evidence objects.

---

### Evidence

Represents an original evidence source associated with a case.

Core fields:

- evidence_id
- case_id
- name
- type
- size
- sha256
- source
- acquisition_time
- ingestion_time
- processing_status
- integrity_status
- storage_reference

Evidence is immutable after ingestion under normal application
operations.

---

### Artifact

Represents a forensic object extracted from Evidence.

Core fields:

- artifact_id
- evidence_id
- artifact_type
- source_location
- parser_name
- parser_version
- extraction_status
- extracted_at
- provenance

Every Artifact must maintain a direct relationship to its source
Evidence.

---

### Event

Represents a normalized activity derived from one or more Artifacts.

Core fields:

- event_id
- artifact_id
- evidence_id
- timestamp
- timestamp_precision
- source
- event_type
- user
- host
- process
- file
- ip
- domain
- hash
- command
- description
- severity
- confidence
- created_at

Every Event must be traceable to its originating Artifact and Evidence.

---

### IOC

Represents an Indicator of Compromise.

Core fields:

- ioc_id
- type
- value
- source
- confidence
- severity
- first_seen
- last_seen

An IOC finding must reference the Event or Artifact that produced the
observation.

---

### Detection

Represents a finding produced by an IOC matcher, rule or anomaly
detector.

Core fields:

- detection_id
- case_id
- detection_type
- severity
- confidence
- rule_id
- rule_version
- model_id
- model_version
- schema_version
- created_at

A Detection must reference the evidence and events supporting the
finding.

---

### Incident

Represents a group of related suspicious detections and events.

Core fields:

- incident_id
- case_id
- title
- severity
- confidence
- status
- created_at
- updated_at

An Incident may reference multiple Events, IOCs and Detections.

---

### Timeline Entry

Represents an investigator-facing chronological representation of an
Event.

Timeline entries must preserve the original Event identity and
provenance.

---

## 6.3.2 Core Relationships

```text
Case
 └── Evidence
      └── Artifact
           └── Event
                ├── IOC
                ├── Detection
                └── Timeline Entry

Event + Detection + IOC
          ↓
       Incident
```

The exact relational schema, indexes and constraints will be defined
before database implementation.

---

## 6.3.3 Failure and Partial-Processing Semantics

Forensic processing must support partial success.

An individual artifact parser failing must not automatically invalidate
the entire investigation.

Supported extraction states:

- pending
- processing
- success
- partial
- failed
- skipped

Each failure must record:

- artifact_id
- parser
- parser_version
- failure_time
- error_category
- safe error description

TRACE-X must distinguish between:

1. No evidence found.
2. Evidence found and successfully parsed.
3. Evidence found but partially parsed.
4. Evidence found but parsing failed.
5. Evidence intentionally skipped.

Downstream systems must not treat missing analysis as evidence of absence.

The investigator interface must clearly communicate when a case has
incomplete processing.

The AI assistant must be informed about relevant processing gaps before
generating conclusions.

---

## 6.4 IOC Engine

The IOC engine identifies indicators such as:

- IP addresses
- Domains
- URLs
- File hashes
- Suspicious filenames
- Registry indicators
- Other supported indicator types

IOC detection in the MVP is deterministic.

Every IOC finding must preserve:

- Source artifact
- Source event
- Detection timestamp
- Detection method
- Confidence
- Severity

---

## 6.5 Rule Engine

The rule engine detects known suspicious patterns.

Example:

```text
PowerShell execution
        +
Suspicious command
        +
External network connection
        ↓
High-confidence detection
```

Rules must be:

- Explainable
- Versioned
- Testable
- Auditable
- Reproducible

Every rule-based Detection must record the rule ID and exact rule version.

---

## 6.6 Anomaly Detection Engine

Anomaly detection is an advanced feature and is not part of the initial
MVP.

An anomaly is meaningful only relative to a defined baseline.

TRACE-X must explicitly define the baseline before anomaly detection is
enabled.

Potential baseline strategies include:

- Per-host historical baseline
- Per-user baseline
- Case-level baseline
- Controlled training dataset

The selected baseline must be documented and experimentally evaluated.

Potential features include:

- Process frequency
- Network connection frequency
- Execution time
- File creation frequency
- PowerShell activity
- Registry modifications
- Rare processes
- Unusual behavior patterns

ML output is a signal for investigation.

It must not independently declare malicious activity.

---

## 6.7 Correlation Engine

The Correlation Engine connects related events, detections and IOCs.

An initial implementation may use deterministic approaches such as:

- Shared entities
- Time-window relationships
- Common process/file/network identifiers
- Evidence provenance
- Explicit detection relationships

Example:

```text
PowerShell execution
       ↓
Suspicious file creation
       ↓
Network connection
       ↓
Persistence modification
```

The exact correlation algorithm will be experimentally evaluated and
may later evolve into graph-based correlation.

Correlation must preserve the underlying evidence relationships.

The Correlation Engine is an advanced feature and is not required for the
initial MVP.

---

## 6.8 Timeline Engine

The Timeline Engine creates chronological representations of normalized
events.

It should support:

- Timestamp ordering
- Timestamp precision
- Event filtering
- Source filtering
- Severity filtering
- Incident filtering
- Evidence references
- Correlated event groups

Timeline construction must remain useful even when some evidence sources
have failed processing.

---

## 6.9 Risk Engine

The Risk Engine combines multiple signals into an explainable
prioritization score.

Potential signals include:

- IOC evidence
- Rule detections
- Anomaly score
- Persistence indicators
- Network behavior
- Event correlation
- Asset/context information

The MVP will initially use a documented deterministic weighted scoring
model.

The exact formula must be experimentally validated.

Example:

```text
IOC evidence          +25
Rule detection        +20
Persistence           +20
Network anomaly       +15
Correlated activity   +20
---------------------------
Total                 100
```

These example weights are illustrative only and must not be treated as
final values until validated.

Every risk score must provide an explanation of its contributing signals.

---

## 6.10 Investigation Graph

TRACE-X may provide a graph representation connecting objects such as:

```text
User
 ↓
Process
 ↓
File
 ↓
Hash
 ↓
Network
 ↓
IP
 ↓
Registry
```

The Investigation Graph is an Advanced feature.

It is primarily a presentation layer over the underlying event/entity
model and should not block the MVP.

---

## 6.11 AI Investigation Assistant

The AI assistant helps investigators understand already-processed
investigation data.

Example questions:

- What happened?
- Why is this incident suspicious?
- What evidence supports this finding?
- What should I investigate next?
- Which attack technique may this behavior resemble?

The AI assistant must never invent forensic evidence.

AI output must distinguish between:

### Observed Evidence

Information directly represented in the processed evidence.

### Inference

A conclusion derived from multiple observed events.

### Recommendation

A suggested next investigative action.

If evidence is incomplete or conflicting, the AI must explicitly state the
limitation.

The AI assistant is an Advanced feature and is not required for MVP.

---

## 6.11.1 AI Grounding Contract

The AI investigation assistant must operate only on structured
investigation data retrieved from TRACE-X.

Each factual claim produced by the assistant must be traceable to one or
more supported TRACE-X objects, such as:

- evidence_id
- artifact_id
- event_id
- detection_id
- incident_id

AI responses should provide citations/references to supporting objects
whenever making factual claims.

The response system must distinguish between:

```text
Observed Evidence
        ↓
Inference
        ↓
Recommendation
```

The system must never present an inference or recommendation as directly
observed evidence.

If available evidence is incomplete, the AI must state the limitation.

The implementation must include automated tests verifying that sample
factual claims resolve to valid TRACE-X evidence references.

---

## 6.12 RAG Knowledge Layer

RAG is not required for the MVP.

Its purpose is to provide contextual cybersecurity knowledge that is not
contained directly in the forensic event store.

Potential uses include:

- Explaining MITRE ATT&CK techniques
- Explaining forensic artifacts
- Providing investigation guidance
- Connecting findings to documented security knowledge

A simple deterministic lookup may be preferred over vector retrieval
when the knowledge source is structured and deterministic lookup is more
accurate and auditable.

The RAG architecture will therefore be validated after the MVP event
model and investigation workflow are stable.

---

## 6.13 Reporting

TRACE-X should generate:

- JSON
- PDF

CSV export may be added as an extension when required.

Reports should contain, where applicable:

- Case information
- Evidence information
- Executive summary
- Key findings
- IOC summary
- Timeline
- Incidents
- Risk assessment
- Supporting evidence
- Recommendations
- Evidence integrity information
- Processing limitations

Reports must not hide incomplete or failed processing.

---

## 6.14 Versioning and Reproducibility

TRACE-X must version important analytical components.

At minimum:

- Event schema version
- Parser version
- Detection rule version
- ML model version
- Risk-scoring version

Every generated Detection must preserve the versions of the components
that produced it.

Investigation reports should record relevant processing and detection
versions so that results can be reproduced or explained later.

Changes to the Event schema must use controlled database migrations.

Schema compatibility must be explicitly tested.

---

# 7. Security and Evidence Integrity

TRACE-X itself is a security-sensitive application.

Security must be treated as a first-class architecture concern.

---

## 7.1 Trust Boundary and Sandbox Architecture

Forensic evidence must be treated as hostile input.

Potentially attacker-controlled content includes:

- File contents
- Filenames
- File metadata
- Registry values
- Embedded strings
- Malformed logs
- Timestamps
- URLs
- Domains
- Command strings

Artifact extraction therefore operates in an isolated processing
environment.

The initial implementation must prioritize:

- Process/container isolation
- Least privilege
- No unnecessary outbound network access
- CPU limits
- Memory limits
- Execution timeouts
- Restricted filesystem access
- Validated structured output
- Safe error handling

No raw untrusted evidence should directly reach the investigator-facing
AI or reporting layer.

---

## 7.2 Access Control and Audit Logging

Initial roles:

### Investigator

Can:

- Create cases
- Ingest evidence
- Run analysis
- Investigate findings
- Generate reports

### Viewer

Can:

- View authorized cases
- View findings

Cannot:

- Modify evidence
- Run privileged operations

### Administrator

Can:

- Manage users
- Manage configuration
- Manage system settings
- Manage access controls

Security-sensitive actions must be logged, including:

- Login/logout
- Case creation
- Evidence ingestion
- Evidence access
- Evidence processing
- Report generation
- Configuration changes
- Detection-rule changes
- User/role changes

Audit events should contain:

- Actor
- Action
- Object
- Timestamp
- Outcome
- Relevant metadata

The audit trail itself must be protected against ordinary modification.

---

# 8. Testing Philosophy

TRACE-X must not be tested only with arbitrary uploaded files.

Testing must include:

1. Unit tests
2. Integration tests
3. End-to-end tests
4. Controlled synthetic scenarios
5. Public forensic datasets where appropriate
6. Controlled attack simulations
7. False-positive testing
8. Performance testing
9. Security testing
10. Failure-mode testing

Every important detection should have known expected behavior whenever
possible.

For any detection:

```text
Known test evidence
        ↓
Expected finding
        ↓
TRACE-X result
        ↓
PASS / FAIL
```

Every pipeline stage must have failure-mode tests.

Examples:

- Corrupt input
- Truncated input
- Empty input
- Malformed metadata
- Unsupported artifact
- Parser timeout
- Parser crash

The system must never silently drop evidence.

---

# 9. Benchmarking

TRACE-X must measure real performance rather than making unsupported
claims.

Potential metrics:

- Detection precision
- Detection recall
- False-positive rate
- Timeline accuracy
- Events processed per second
- Processing time
- Memory usage
- CPU usage
- Database query latency
- Worker throughput
- Investigation time
- Report generation time

A major evaluation question is:

> Can TRACE-X reduce the time required for initial cyber triage compared
> with a conventional/manual workflow?

All benchmark values must be experimentally measured.

No benchmark result may be fabricated or presented before measurement.

---

# 10. Existing Solutions

TRACE-X acknowledges existing digital-forensics and DFIR solutions,
including tools such as:

- Autopsy
- Velociraptor
- Timesketch
- Other forensic and incident-response platforms

TRACE-X does not claim that digital forensics is a new problem.

Its intended differentiation is:

- Automated initial triage
- Evidence-backed correlation
- Explainable prioritization
- Investigation timeline
- Attack-story reconstruction
- Integrated investigation workflow
- Evidence-grounded AI assistance
- Local-first/privacy-aware architecture

These differentiators must be evaluated experimentally rather than
claimed without evidence.

---

# 11. Deployment Philosophy

Development is local-first.

Primary development environment:

- macOS
- Docker
- Local PostgreSQL
- Local Redis
- Local object storage
- Local forensic processing
- Local ML
- Optional local LLM

Cloud deployment may be added later for:

- Demonstration
- Collaboration
- Public documentation
- Optional hosted services

Large forensic evidence should not unnecessarily travel through ordinary
API requests.

---

# 12. Technology Stack

## 12.1 Frontend

- Next.js
- TypeScript
- React
- Tailwind CSS

## 12.2 Backend

- Python
- FastAPI

## 12.3 Database

- PostgreSQL

## 12.4 Queue / Cache

- Redis

## 12.5 Background Processing

- Celery or another appropriate worker framework

## 12.6 Storage

- S3-compatible storage
- MinIO for local development

## 12.7 Machine Learning

Initial:

- Python
- scikit-learn

Additional ML tooling may be evaluated later.

## 12.8 AI / RAG

- Provider-agnostic architecture
- Local models where practical
- Optional external providers
- Open-source/local vector storage where appropriate

AI provider choice must never become a hard dependency of core
forensic analysis.

## 12.9 Infrastructure

- Docker
- Docker Compose
- Git
- GitHub
- GitHub Actions

Specific library choices require review before implementation.

---

# 13. Core Design Principles

1. Evidence first.
2. Automation second.
3. AI last.
4. Explainability over black-box claims.
5. Original evidence must remain immutable.
6. Every derived finding must maintain provenance.
7. Security is a core feature.
8. Tests are part of implementation, not an afterthought.
9. Benchmark claims must be experimentally supported.
10. Prefer modular and replaceable components.
11. Avoid unnecessary dependencies.
12. Preserve reproducibility.
13. Do not build features only for visual demonstration.
14. Do not claim forensic capabilities that are not actually implemented.
15. Missing analysis must never be interpreted as absence of evidence.
16. Prefer deterministic methods when they are more reliable and
    auditable than AI methods.
17. Every important automated conclusion must remain traceable to source
    evidence.

---

# 14. Scope Strategy

## 14.1 MVP

The MVP focuses on a small but genuinely working forensic workflow.

### Evidence

- Case management
- Evidence ingestion
- SHA-256 hashing
- Evidence integrity
- Sandboxed processing architecture

### Artifact Extraction

Initial MVP artifact types:

1. Filesystem metadata
2. Windows Event Logs
3. Windows Registry

### Analysis

- Defined Event model
- PostgreSQL event store
- Deterministic IOC detection
- Small versioned rule engine
- Basic explainable risk scoring
- Timeline

### Reporting

- JSON
- PDF

### Security

- Basic authentication
- Single investigator role
- Audit logging
- Evidence integrity controls

---

## 14.2 Advanced

After MVP stability:

- Correlation Engine
- Anomaly Detection
- Investigation Graph
- Evidence-grounded AI Assistant
- RAG
- Advanced artifact types
- Advanced reporting
- Performance optimization
- Multi-user RBAC

---

## 14.3 Future Research / Scale

- Distributed processing
- Multi-machine investigations
- Large-scale evidence processing
- Plugin architecture
- Additional operating systems
- Advanced ML
- Advanced threat-intelligence integrations
- Advanced investigation automation

---

## 14.4 Explicit Non-Priorities

The following must not delay the MVP:

- Cloud deployment
- Multi-user collaboration
- Plugin architecture
- Complex graph visualization
- Large-scale distributed processing
- Advanced LLM functionality

---

# 15. Success Criteria

TRACE-X will be considered successful when it can demonstrate that:

1. Evidence can be ingested while maintaining integrity.
2. Real or controlled forensic artifacts can be extracted.
3. Artifacts can be normalized into a common event model.
4. Suspicious indicators can be detected.
5. Findings can be traced back to source evidence.
6. A useful investigation timeline can be generated.
7. Findings receive explainable prioritization.
8. Processing failures are visible to investigators.
9. Reports can be generated.
10. The system passes defined test scenarios.
11. Performance and detection results can be measured.
12. The entire workflow is reproducible.
13. No unsupported claims are presented as facts.
14. The architecture remains understandable and maintainable.

---

# 16. Definition of Done

A feature is not considered complete merely because code exists.

A feature is complete only when:

- Implementation exists.
- Required tests exist.
- Tests pass.
- Security considerations are addressed.
- Error handling exists.
- Documentation is updated.
- Relevant architecture is preserved.
- Provenance/evidence requirements are satisfied where applicable.
- Acceptance criteria are satisfied.
- STATUS.md is updated.

Additional requirements:

- Every detection type must have a test fixture with known ground truth.
- Every pipeline stage must have failure-mode tests.
- Corrupt/truncated input must not silently disappear.
- Partial processing must be visible to investigators.
- AI features must have evidence-grounding tests.
- Event schema changes must have migration/compatibility tests.
- Benchmark results must come from reproducible test scenarios.
- A feature cannot be marked complete based solely on UI appearance.
- A feature cannot be marked complete if its underlying behavior is
  mocked or fabricated.

---

# 17. Specification Governance

TRACE-X is a long-term project.

This document is a living technical specification.

Major changes to:

- Product scope
- Core architecture
- Trust boundaries
- Data model
- Security model
- Processing pipeline
- Technology foundations

must be documented and reviewed before implementation.

Each major specification revision should increment the version number.

### Specification Version History

```text
v0.1 → Initial specification
v0.2 → Architecture refinement
v0.3 → Data model finalized
v1.0 → Stable release specification
```

Architecture decisions that materially affect implementation should be
recorded in the project's architectural decision documentation.

---

# 18. Current Status

Current specification version:

**0.2**

Current development state:

**Pre-development / Architecture phase**

Application implementation has not started.

The next engineering steps are:

1. Finalize TRACESPEC.
2. Create BRAIN.md.
3. Create AGENTS.md.
4. Create PIPELINE.md.
5. Create ROADMAP.md.
6. Create STATUS.md.
7. Create initial TRACE-X agent skills.
8. Perform final architecture review.
9. Begin foundation implementation.