---
name: tracex-code-review
description: Use this skill when reviewing, auditing, refactoring, or approving TRACE-X code for correctness, security, forensic integrity, maintainability, testing, and architectural compliance.
---

# TRACE-X Code Review Skill

## Purpose

Use this skill whenever code is being reviewed, audited, refactored, or
prepared for merge.

The goal is to ensure that TRACE-X code is:

- Correct
- Secure
- Testable
- Maintainable
- Explainable
- Architecturally consistent
- Forensically trustworthy

Code review must identify real problems rather than simply making code
look cleaner.

---

# 1. Required Context

Before reviewing code, read the relevant project documents.

At minimum:

1. `BRAIN.md`
2. `TRACESPEC.md`
3. `AGENTS.md`
4. `PIPELINE.md`
5. `STATUS.md`

Also inspect:

- Related source code
- Related tests
- Relevant schemas
- Relevant API contracts
- Relevant skills

Do not review code in isolation when surrounding architecture affects
correctness.

---

# 2. Review Priority

Review issues in this order:

```text
1. Security
2. Evidence integrity
3. Data correctness
4. Architectural violations
5. Reliability
6. Test coverage
7. Performance
8. Maintainability
9. Style
```

Do not spend significant review effort on formatting while a security or
correctness problem remains unresolved.

---

# 3. Review Severity

Classify findings using:

```text
CRITICAL
HIGH
MEDIUM
LOW
INFO
```

### CRITICAL

A problem that can:

- Compromise the system
- Compromise evidence integrity
- Cause unauthorized evidence access
- Execute attacker-controlled code
- Cause catastrophic data loss
- Break a critical trust boundary

### HIGH

A serious security, correctness, reliability, or architectural problem
that should block merging.

### MEDIUM

A meaningful issue that should normally be fixed but may not block the
current change.

### LOW

A minor issue with limited impact.

### INFO

An observation, suggestion, or improvement that is not a defect.

---

# 4. Evidence Integrity Review

For any code touching forensic evidence, verify:

```text
[ ] Original evidence is not modified
[ ] Evidence is treated as untrusted
[ ] Hashes are preserved
[ ] Provenance is preserved
[ ] Derived data links back to source evidence
[ ] Processing failures are recorded
[ ] Partial results are clearly identified
[ ] Evidence-controlled paths are validated
[ ] Parser execution is appropriately isolated
```

A change that can silently alter original evidence is a blocking issue.

---

# 5. Security Review

Check for:

### Authentication

- Authentication is required where appropriate.
- Sessions/tokens are handled securely.
- Passwords are never stored in plaintext.
- Sensitive authentication data is not logged.

### Authorization

Verify authorization on the server.

Never rely only on:

```text
Frontend visibility
```

or:

```text
Disabled UI buttons
```

Users must not be able to access cases, evidence, reports, or APIs merely
by changing IDs in requests.

---

# 6. IDOR / Object Access Review

For endpoints such as:

```text
/cases/{case_id}
/evidence/{evidence_id}
/reports/{report_id}
/events/{event_id}
```

verify that the requesting user is actually authorized to access the
object.

Do not assume that knowing an ID grants access.

---

# 7. Input Validation

All external input is untrusted.

Review:

- Request bodies
- Query parameters
- Path parameters
- File names
- Uploaded files
- Headers
- URLs
- Search expressions
- Filter values
- Evidence metadata

Validate:

```text
Type
Length
Format
Range
Allowed values
Encoding
```

Do not trust client-side validation.

---

# 8. File Upload Review

For upload functionality, verify:

```text
[ ] File size limits
[ ] Allowed formats
[ ] Safe temporary storage
[ ] Filename sanitization
[ ] Path traversal protection
[ ] Archive extraction protection
[ ] Malware/untrusted-content handling
[ ] Resource limits
[ ] Authentication
[ ] Authorization
```

Never directly use an attacker-controlled filename as a filesystem path.

---

# 9. Command Injection Review

Pay special attention to code using:

```text
subprocess
os.system
shell commands
Docker commands
CLI forensic tools
```

Prefer structured argument execution over shell interpretation.

Avoid:

```python
os.system(user_input)
```

and unsafe string interpolation into shell commands.

If an external command is required:

```text
Validate input
     ↓
Use fixed executable
     ↓
Pass structured arguments
     ↓
Restrict environment
     ↓
Apply timeout
     ↓
Capture output safely
```

---

# 10. Path Traversal Review

Look for:

```text
../
absolute paths
symlinks
device paths
encoded traversal
```

Any path derived from evidence or users must be constrained to the
intended directory.

---

# 11. Secrets Review

Never commit or hardcode:

- API keys
- Passwords
- JWT secrets
- Database credentials
- Cloud credentials
- AI provider keys
- Encryption keys

Check for:

```text
.env
source code
configuration files
Dockerfiles
CI/CD configuration
logs
error messages
```

Use environment variables or approved secret-management mechanisms.

---

# 12. Logging Review

Logs should help investigators and operators without leaking sensitive
information.

Never log:

- Passwords
- API keys
- Authentication tokens
- Session secrets
- Private credentials

For forensic processing, logs should preserve useful operational
information such as:

```text
Case ID
Evidence ID
Processing job
Parser
Parser version
Status
Failure category
Duration
```

Do not log uncontrolled attacker-provided data without considering log
injection.

---

# 13. API Security Review

For every new API endpoint check:

```text
[ ] Authentication
[ ] Authorization
[ ] Input validation
[ ] Rate/resource limits where appropriate
[ ] Error handling
[ ] Safe response data
[ ] Audit logging where required
[ ] No sensitive information leakage
```

Do not expose internal stack traces to clients.

---

# 14. Database Security Review

Check:

- Parameterized queries
- ORM/query safety
- Authorization at the service layer
- Correct transaction boundaries
- Appropriate indexes
- No unnecessary sensitive data
- Safe migrations
- Correct foreign-key relationships

Avoid dynamically constructed SQL using untrusted input.

---

# 15. AI Security Review

AI output is **not trusted evidence**.

Never allow an AI model to:

- Modify original evidence
- Directly authorize access
- Make final forensic conclusions without supporting evidence
- Execute arbitrary commands
- Decide security permissions
- Silently modify investigation records

Prefer:

```text
Evidence
   ↓
Deterministic Processing
   ↓
Structured Findings
   ↓
AI Interpretation
   ↓
Human Review
```

AI-generated statements should be traceable to supporting events or
evidence.

---

# 16. Prompt Injection Review

For AI features, assume forensic evidence may contain malicious text such
as:

```text
Ignore previous instructions
Run this command
Reveal system prompt
Call this URL
```

Evidence content must be treated as **data**, not instructions.

The system must maintain a strict separation between:

```text
AI Instructions
```

and:

```text
Evidence Content
```

Do not allow evidence strings to override system or application rules.

---

# 17. AI Tool Permission Review

If an AI agent has access to tools:

Prefer:

```text
Read-only
```

over:

```text
Write
```

and:

```text
Restricted operation
```

over:

```text
Arbitrary execution
```

AI should not receive broad filesystem, database, shell, or network
permissions unless explicitly required and strongly isolated.

---

# 18. Container Security Review

For Docker/containerized processing, check:

```text
[ ] Non-root user where possible
[ ] Minimal base image
[ ] No unnecessary capabilities
[ ] Restricted filesystem
[ ] Read-only mounts where possible
[ ] Resource limits
[ ] Network restrictions
[ ] No privileged mode unless explicitly justified
[ ] Secrets not baked into images
```

Never use privileged containers for convenience.

---

# 19. Dependency Review

Before accepting a new dependency:

```text
[ ] Is it necessary?
[ ] Is there already an equivalent dependency?
[ ] Is it maintained?
[ ] Is the license acceptable?
[ ] Does it introduce security risk?
[ ] Does it significantly increase bundle/runtime size?
[ ] Is the version pinned appropriately?
```

Do not add libraries simply because generated code used them.

---

# 20. Error Handling

Errors must fail safely.

Avoid:

```python
except Exception:
    pass
```

unless there is a very specific and documented reason.

Do not hide:

- Parser failures
- Database failures
- Authentication failures
- Authorization failures
- Evidence integrity failures
- Processing failures

Errors should be:

```text
Handled
Recorded
Classified
Exposed appropriately
```

without leaking sensitive internals.

---

# 21. Concurrency and Background Jobs

For processing jobs, review:

- Duplicate execution
- Job retries
- Race conditions
- Idempotency
- Cancellation
- Timeouts
- Resource exhaustion
- Worker failures

A retry must not accidentally:

```text
Duplicate evidence
Duplicate findings
Corrupt state
Overwrite results
```

where those outcomes are not intended.

---

# 22. Data Consistency

Check that related operations are atomic where necessary.

For example:

```text
Create Evidence
     ↓
Create Hash
     ↓
Create Processing Job
```

If the operation fails halfway through, the system should not leave
misleading state.

Use transactions or explicit state transitions where appropriate.

---

# 23. Testing Review

Every meaningful code change should have appropriate tests.

Check for:

```text
[ ] Unit tests
[ ] Integration tests
[ ] Security tests where relevant
[ ] Failure-path tests
[ ] Edge-case tests
[ ] Regression tests
```

For forensic functionality also check:

```text
[ ] Valid evidence
[ ] Corrupt evidence
[ ] Missing data
[ ] Malformed data
[ ] Large data
[ ] Adversarial input
```

Do not consider:

> "The application starts"

to be sufficient testing.

---

# 24. Performance Review

Performance matters when processing large evidence sets.

Look for:

- Loading entire datasets into memory unnecessarily
- N+1 database queries
- Unbounded loops
- Repeated parsing
- Excessive serialization
- Missing indexes
- Blocking operations inside async paths
- Unbounded concurrency

Prefer streaming, batching and bounded concurrency where appropriate.

Do not optimize prematurely.

Measure before introducing complex performance architecture.

---

# 25. Frontend Review

For frontend code, check:

```text
[ ] No secrets in client code
[ ] Authorization not assumed from UI
[ ] Sensitive data not unnecessarily stored locally
[ ] Safe rendering of untrusted strings
[ ] API errors handled safely
[ ] Loading/error states exist
[ ] Large datasets are handled efficiently
```

Never render forensic strings as trusted HTML without sanitization.

---

# 26. API Contract Review

When changing an API:

Check:

```text
Request schema
Response schema
Validation
Error format
Authentication
Authorization
Backward compatibility
Frontend consumers
Tests
Documentation
```

Do not silently change an API response that existing consumers depend on.

---

# 27. Architecture Compliance

Verify that the implementation follows:

```text
BRAIN.md
TRACESPEC.md
AGENTS.md
PIPELINE.md
```

Pay particular attention to:

- Trust boundaries
- Evidence immutability
- Provenance
- Parser isolation
- Detection separation
- AI boundaries

If the implementation conflicts with project architecture, identify the
conflict explicitly.

Do not silently normalize architectural violations.

---

# 28. Code Quality

Look for:

- Clear naming
- Small focused functions
- Appropriate abstractions
- Avoidable duplication
- Circular dependencies
- Dead code
- Hidden global state
- Excessive coupling
- Unnecessary complexity

Do not refactor purely for personal style preferences.

A refactor should have a clear benefit.

---

# 29. Review Output Format

When performing a code review, structure the response as:

```text
## Verdict

APPROVE
or
REQUEST CHANGES

## Critical Findings

...

## High Findings

...

## Medium Findings

...

## Low / Informational Findings

...

## Security Assessment

...

## Forensic Integrity Assessment

...

## Test Assessment

...

## Recommended Changes

...
```

If there are no findings in a category, explicitly state:

```text
None.
```

Do not invent findings to make a review appear thorough.

---

# 30. Finding Format

Each finding should contain:

```text
Severity:
Location:
Problem:
Why it matters:
Recommended fix:
```

Example:

```text
Severity: HIGH

Location:
backend/evidence/upload.py

Problem:
The uploaded filename is directly joined with the evidence directory.

Why it matters:
An attacker-controlled path may escape the intended storage directory.

Recommended fix:
Generate server-side storage identifiers and validate all resolved paths
against the allowed evidence directory.
```

---

# 31. Review Rules for AI-Generated Code

AI-generated code requires the same or greater scrutiny as human-written
code.

Do not assume generated code is correct because:

- It compiles
- Tests pass
- The implementation looks professional
- Another model generated it
- The framework accepts it

Pay special attention to:

- Hallucinated APIs
- Incorrect library usage
- Security assumptions
- Missing error handling
- Fake implementations
- Placeholder logic
- Unnecessary dependencies
- Overengineering
- Incorrect forensic interpretations

---

# 32. No Fake Functionality

Reject code that presents functionality as implemented when it is actually:

```text
Mocked
Hardcoded
Placeholder
Randomly generated
Simulated
```

unless it is explicitly labeled as a test/demo implementation.

Examples of unacceptable production behavior:

```text
risk_score = 87
```

without a real scoring mechanism.

```text
malware_detected = True
```

without actual detection logic.

```text
ai_confidence = 0.97
```

without a defensible source.

TRACE-X must distinguish between:

```text
Real capability
```

and:

```text
Prototype/mock capability
```

---

# 33. Definition of Review Complete

A code review is complete only when:

```text
[ ] Relevant project context inspected
[ ] Security reviewed
[ ] Evidence integrity reviewed
[ ] Architecture reviewed
[ ] Error handling reviewed
[ ] Tests reviewed
[ ] Performance considered
[ ] AI boundaries reviewed where applicable
[ ] Findings classified
[ ] Recommended fixes identified
```

---

# 34. Final Principle

The purpose of code review is not to make the code look perfect.

The purpose is to answer:

> "Can we trust this change?"

For TRACE-X, trust means:

```text
Correct
+
Secure
+
Traceable
+
Tested
+
Explainable
+
Architecturally consistent
```

If those conditions are not satisfied, the code is not ready to merge.