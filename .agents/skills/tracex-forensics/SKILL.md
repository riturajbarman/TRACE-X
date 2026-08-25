---
name: tracex-forensics
description: Use this skill when working with digital forensic evidence, artifact extraction, forensic parsers, provenance, hashing, evidence integrity, forensic timestamps, or sandboxed analysis.
---

# TRACE-X Forensics Skill

## Purpose

Use this skill whenever a task involves forensic evidence or the extraction,
interpretation, normalization or handling of forensic artifacts.

The primary objective is:

> Extract useful forensic information without compromising evidence
> integrity, provenance, security or reproducibility.

---

# 1. Core Forensic Principles

Always follow:

```text
Evidence
   ↓
Preserve
   ↓
Validate
   ↓
Extract
   ↓
Normalize
   ↓
Analyze
```

Never treat raw forensic evidence as trusted application data.

Never modify original evidence during normal analysis.

Never create a forensic conclusion without traceable supporting data.

---

# 2. Evidence Is Hostile Input

Treat all evidence content as potentially attacker-controlled.

This includes:

- File contents
- File names
- File paths
- Registry values
- Event-log fields
- Embedded strings
- URLs
- Domains
- IP addresses
- Commands
- Metadata
- Timestamps
- Encoded data
- Malformed structures

Do not assume that forensic evidence is safe merely because it came from
a disk image, log archive or investigation package.

Evidence may contain data deliberately designed to exploit parsers.

---

# 3. Evidence Integrity

Original evidence must be immutable.

Before processing:

```text
Evidence
   ↓
SHA-256
   ↓
Integrity Record
```

Record:

- evidence_id
- filename/name
- size
- SHA-256
- source
- ingestion timestamp
- acquisition metadata when available
- integrity status

Never overwrite or modify the original evidence.

Do not use original evidence as a writable workspace.

Use:

- read-only mounts
- controlled working copies
- isolated processing environments

according to the approved architecture.

---

# 4. Hashing Rules

When handling evidence:

1. Calculate the configured cryptographic hash before analysis.
2. Store the hash with the Evidence record.
3. Preserve the exact source identity.
4. Do not silently replace the original file.
5. Recalculate/verify the hash when integrity verification is required.
6. Record integrity failures explicitly.

Do not treat a changed hash as a harmless warning.

---

# 5. Provenance

Every extracted object must preserve its source.

The required conceptual chain is:

```text
Case
 ↓
Evidence
 ↓
Artifact
 ↓
Event
 ↓
Detection / IOC
 ↓
Incident
```

A derived object should answer:

> "Which evidence source produced this result?"

At minimum, preserve:

- evidence_id
- artifact_id where applicable
- source location
- parser name
- parser version
- extraction timestamp
- processing status

Never produce a detached forensic finding that cannot be traced to its
source.

---

# 6. Parser Design

Every forensic parser should be isolated behind a clear interface.

A parser should conceptually provide:

```text
Input
 ↓
Validation
 ↓
Parsing
 ↓
Structured Artifact
 ↓
Status / Error
```

A parser should expose or record:

- parser_name
- parser_version
- input_type
- artifact_type
- extraction_status
- provenance
- error information

Parsers must not contain unrelated business logic.

---

# 7. Parser Safety

A parser must assume that input may be:

- Corrupt
- Truncated
- Malformed
- Unexpected
- Extremely large
- Adversarial
- Unsupported

A parser must not assume well-formed input.

Never let a malformed artifact crash the entire case-processing pipeline.

Use safe exception handling around parser boundaries.

---

# 8. Sandbox Requirements

Artifact extraction belongs to the untrusted processing zone.

Preferred conceptual architecture:

```text
Original Evidence
       ↓
Controlled Access
       ↓
Sandboxed Worker
       ↓
Parser
       ↓
Validated Structured Output
       ↓
Trusted Processing
```

The sandbox should use, where supported by the implementation:

- Least privilege
- Restricted filesystem access
- Restricted network access
- CPU limits
- Memory limits
- Timeouts
- Process isolation
- Temporary working directories

Do not execute content from evidence as an operating-system instruction.

---

# 9. Network Policy

Forensic extraction should not require unrestricted internet access.

Default expectation:

```text
Network access = Disabled / Restricted
```

Only explicitly approved functionality should make outbound network
connections.

A parser should not unexpectedly:

- Download files
- Contact remote domains
- Resolve arbitrary URLs
- Query external services

unless that behavior is explicitly part of the approved architecture.

---

# 10. Filesystem Safety

Never trust a path originating from evidence.

Watch for:

- Path traversal
- Absolute paths
- Symlinks
- Special files
- Device paths
- Unexpected encodings
- Very long paths
- Resource exhaustion

Never allow evidence-controlled paths to escape the intended sandbox
directory.

---

# 11. Artifact Extraction States

Each extraction job should use explicit states:

```text
PENDING
PROCESSING
SUCCESS
PARTIAL
FAILED
SKIPPED
```

Do not collapse all failures into `SUCCESS`.

---

# 12. Partial Processing

Forensic datasets are often incomplete.

Examples:

```text
Registry hive → SUCCESS
Event log     → PARTIAL
Other log     → FAILED
```

The case must still be able to continue when safe.

However:

> Missing analysis must never be interpreted as absence of evidence.

The investigator must be able to see what was:

- successfully processed
- partially processed
- failed
- skipped

The AI investigation layer must also be aware of relevant processing gaps.

---

# 13. Timestamp Handling

Forensic timestamps require special care.

Never silently assume that all timestamps:

- use the same timezone
- have the same precision
- are trustworthy
- represent the same semantic event time

Where possible, preserve:

- original timestamp
- normalized timestamp
- timestamp precision
- timezone information
- timestamp source
- timestamp interpretation

If the timestamp's meaning is uncertain, preserve that uncertainty.

---

# 14. Event Normalization

Artifact-specific data should be transformed into the common TRACE-X Event
model.

Conceptually:

```text
Registry
   ↓
Registry Artifact
   ↓
Normalized Event
```

```text
Event Log
   ↓
Event Artifact
   ↓
Normalized Event
```

```text
Filesystem
   ↓
Filesystem Artifact
   ↓
Normalized Event
```

Do not throw away important provenance during normalization.

The normalized Event must remain connected to its original Artifact and
Evidence.

---

# 15. No Premature Interpretation

Artifact extraction should primarily answer:

> "What data is present?"

Detection should answer:

> "What does this data indicate?"

Do not place large amounts of detection logic inside low-level parsers.

Prefer:

```text
Parser
 ↓
Artifact
 ↓
Normalizer
 ↓
Event
 ↓
Detection Engine
```

rather than:

```text
Parser
 ↓
"Malware detected"
```

---

# 16. Detection vs Evidence

The following are different concepts:

```text
Evidence
```

What was observed.

```text
Detection
```

What a rule or analytical method identified.

```text
Inference
```

What multiple observations may imply.

Never confuse these levels.

For example:

Bad:

> "This registry key proves malware."

Better:

> "This registry key was observed and matches rule DET-014 associated
> with a persistence pattern."

---

# 17. Forensic Error Reporting

Parser failures should record useful but safe information.

Recommended fields:

- artifact_id
- parser_name
- parser_version
- failure_time
- error_category
- safe_error_message
- processing_stage

Avoid exposing:

- Secrets
- Internal credentials
- Sensitive system information
- Full attacker-controlled payloads in unsafe contexts

Do not silently discard errors.

---

# 18. Resource Limits

Forensic input may be extremely large.

Processing components should consider limits for:

- File size
- Decompression size
- CPU time
- Memory
- Number of files
- Number of events
- Processing duration

Resource-exhaustion protection is part of forensic parser security.

---

# 19. Decompression Safety

If archives or compressed evidence are supported:

Be aware of:

- Archive bombs
- Excessive nesting
- Excessive expansion ratio
- Huge member counts
- Path traversal
- Symlink extraction

Never blindly extract an archive into an unrestricted directory.

---

# 20. Evidence Access

Only authorized components and users should access evidence.

Separate:

```text
Original Evidence
```

from:

```text
Derived Data
```

and:

```text
Application Logs
```

Do not mix all three into the same writable storage location.

---

# 21. Forensic Reproducibility

A forensic processing result should be reproducible.

Preserve enough metadata to identify:

- Evidence hash
- Parser version
- Schema version
- Rule version
- Model version where applicable
- Processing timestamp
- Relevant configuration

A later result should be explainable in terms of the software versions
that produced it.

---

# 22. Testing Requirements

Every parser should have tests for at least:

### Valid Input

Expected artifact is extracted.

### Empty Input

Handled safely.

### Corrupt Input

Parser fails safely.

### Truncated Input

Parser fails or returns partial status safely.

### Unsupported Input

Explicitly rejected or skipped.

### Maliciously Crafted Input

Parser must not escape its processing boundary or crash the application.

### Large Input

Resource limits are respected.

---

# 23. Test Fixture Requirements

Prefer controlled fixtures.

Example:

```text
tests/
└── fixtures/
    ├── registry/
    ├── eventlogs/
    └── filesystem/
```

Each fixture should have known expected output.

Conceptually:

```text
Fixture
  ↓
Parser
  ↓
Actual Output
  ↓
Expected Output
  ↓
PASS / FAIL
```

Do not validate a parser merely because it "did not crash."

Validate the extracted content.

---

# 24. Parser Completion Checklist

Before a parser is considered complete:

```text
[ ] Input contract defined
[ ] Parser interface implemented
[ ] Parser version defined
[ ] Valid fixture exists
[ ] Expected output defined
[ ] Empty input tested
[ ] Corrupt input tested
[ ] Truncated input tested
[ ] Unsupported input tested
[ ] Resource behavior considered
[ ] Errors handled
[ ] Provenance preserved
[ ] Artifact status recorded
[ ] Events can trace back to the artifact
[ ] Documentation updated
```

---

# 25. Forensic Implementation Workflow

For new forensic functionality:

```text
Understand Artifact
        ↓
Define Input
        ↓
Define Parser Contract
        ↓
Create Fixture
        ↓
Implement Parser
        ↓
Test
        ↓
Normalize
        ↓
Verify Provenance
        ↓
Integrate
        ↓
Test Full Pipeline
```

Do not begin with a large implementation.

Start with one artifact type and one known fixture.

---

# 26. What This Skill Must Prevent

This skill exists specifically to prevent the following:

- Modifying original evidence
- Trusting attacker-controlled strings
- Executing evidence content
- Running parsers without isolation
- Losing provenance
- Silently ignoring parser failures
- Treating missing data as evidence of absence
- Mixing parsing with detection logic
- Fabricating forensic findings
- Creating untraceable analytical results
- Allowing one bad artifact to crash an entire investigation
- Making unsupported forensic claims

---

# 27. Final Principle

Forensic software must be conservative.

When uncertain:

```text
Preserve
   ↓
Record
   ↓
Expose uncertainty
```

Do not silently normalize away uncertainty.

Do not silently discard evidence.

Do not silently invent an interpretation.

The objective is not:

> "Make the forensic data look clean."

The objective is:

> "Preserve the evidence, extract what can be reliably extracted, and
> make the limits of the analysis visible."