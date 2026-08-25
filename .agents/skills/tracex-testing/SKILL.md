---
name: tracex-testing
description: Use this skill when designing, implementing, reviewing, or modifying TRACE-X tests, test fixtures, parser tests, API tests, security tests, integration tests, end-to-end tests, or validation workflows.
---

# TRACE-X Testing Skill

## Purpose

Use this skill whenever a change needs to be tested or validated.

The goal is to ensure TRACE-X is:

- Correct
- Secure
- Deterministic where expected
- Explainable
- Reproducible
- Resistant to malformed input
- Safe under failure
- Maintainable

Testing is part of implementation, not a final step after implementation.

---

# 1. Testing Principles

TRACE-X follows these principles:

- Test behavior, not implementation details.
- Every important feature must have tests.
- Security-sensitive behavior must have explicit tests.
- Forensic parsers must use known fixtures.
- Malformed input must be tested.
- Failure paths must be tested.
- Do not rely only on happy-path tests.
- Tests must be reproducible.
- Avoid tests that depend on external services unless explicitly required.
- Do not weaken production security simply to make tests pass.

---

# 2. Testing Layers

Prefer multiple testing layers:

```text
Unit Tests
    ↓
Integration Tests
    ↓
Security Tests
    ↓
End-to-End Tests

Use the smallest appropriate test for each behavior.

3. Unit Tests

Unit tests should verify isolated behavior.

Examples:

Hash calculation
Event normalization
IOC extraction
Risk calculation
Rule evaluation
Timestamp normalization
Parser behavior
Validation logic

A unit test should generally have:

Arrange
   ↓
Act
   ↓
Assert

Example:

Input
  ↓
Function
  ↓
Expected Output
4. Forensic Parser Tests

Every forensic parser must have controlled test fixtures.

Example:

tests/
└── fixtures/
    ├── registry/
    ├── eventlogs/
    ├── browser/
    ├── prefetch/
    └── filesystem/

For each parser test:

Known Fixture
      ↓
Parser
      ↓
Expected Structured Output

Do not consider a parser tested merely because it does not crash.

Verify the actual extracted values.

5. Required Parser Test Cases

Where applicable, every parser should test:

[ ] Valid input
[ ] Empty input
[ ] Corrupt input
[ ] Truncated input
[ ] Unsupported input
[ ] Unexpected encoding
[ ] Large input
[ ] Malformed fields
[ ] Missing optional fields
[ ] Invalid timestamps
[ ] Multiple records
[ ] Duplicate records

The parser must fail safely.

A bad artifact must not crash the entire processing pipeline.

6. Security Testing

Security-sensitive behavior must have explicit tests.

Test:

Authentication
Authorization
Case isolation
Evidence access control
Input validation
Path traversal protection
File upload restrictions
API authorization
Secret handling
Rate limiting where applicable
Sandbox boundaries
Resource limits
Dangerous file handling

Example:

User A
  ↓
Request Case B
  ↓
403 / Access Denied

This should be tested explicitly.

7. API Tests

API tests should verify:

Authentication
Authorization
Input validation
Response schema
Error handling
Status codes

Test both valid and invalid requests.

Examples:

Valid request       → 200
Invalid input       → 400
Unauthenticated     → 401
Unauthorized        → 403
Missing resource    → 404
Unexpected failure  → safe 5xx response

Do not expose internal stack traces or sensitive information in API responses.

8. Database Tests

Database behavior should be tested where it affects application correctness.

Test:

Evidence relationships
Case isolation
Event relationships
Provenance relationships
Constraints
Unique identifiers
Required fields
Cascading behavior
Migration correctness

Never assume database constraints are correct simply because the ORM model looks correct.

9. Integration Tests

Integration tests should verify that components work together.

Examples:

Evidence
   ↓
Hashing
   ↓
Artifact Extraction
   ↓
Normalization
   ↓
Event Storage

Or:

Event
   ↓
IOC Detection
   ↓
Rule Engine
   ↓
Correlation
   ↓
Risk Score

Integration tests should verify real interfaces between components.

Avoid replacing every dependency with mocks.

10. End-to-End Tests

Critical investigator workflows should have end-to-end tests.

Example:

Login
  ↓
Create Case
  ↓
Upload Evidence
  ↓
Process Evidence
  ↓
View Findings
  ↓
Open Timeline
  ↓
Inspect IOC
  ↓
Generate Report

The test should verify the complete workflow.

11. Failure Testing

TRACE-X must be tested under failure conditions.

Examples:

Parser crashes
Database unavailable
Redis unavailable
Worker timeout
Invalid evidence
Corrupt archive
Storage failure
Large evidence package
AI provider unavailable
Report generation failure

Expected behavior should be explicit.

The system should:

Fail safely
Preserve existing evidence
Record the failure
Avoid corrupting case state
Allow recovery where possible
Inform the investigator clearly
12. AI Testing

AI output must never be treated as automatically correct.

Test:

Hallucinated conclusions
Missing evidence
Incorrect interpretation
Unsupported claims
Prompt injection attempts
Malicious evidence text
Conflicting evidence
AI provider failure
AI timeout
AI unavailable

AI-generated findings should remain traceable to underlying evidence.

13. Determinism

The following should be deterministic where possible:

Hashing
Parsing
Normalization
IOC matching
Rule evaluation
Risk calculations based on fixed inputs

For example:

Same Evidence
+
Same Parser Version
+
Same Configuration
        ↓
Same Result

If a component is intentionally non-deterministic, document why.

14. Regression Testing

When a bug is fixed:

Bug Found
   ↓
Regression Test Added
   ↓
Bug Fixed
   ↓
Full Relevant Test Suite

Never rely only on manually verifying that the bug disappeared.

The test should prevent the same bug from returning.

15. Test Data Safety

Do not place real sensitive forensic evidence in the repository.

Prefer:

Synthetic fixtures
Sanitized datasets
Public forensic datasets where permitted
Minimal reproducible examples

Never commit:

Credentials
API keys
Private case data
Real investigator information
Sensitive evidence
Production tokens
16. Test Isolation

Tests should not unexpectedly modify:

Production databases
Production evidence
Production object storage
Real investigator accounts
External systems

Use isolated test environments.

Example:

Development
     ↓
Test Database
     ↓
Test Storage
     ↓
Test Workers

Do not point automated tests at production infrastructure.

17. Test Naming

Test names should explain the expected behavior.

Prefer:

test_parser_returns_partial_status_for_corrupt_optional_artifact()

over:

test_parser_2()

A test name should help explain what broke when the test fails.

18. Coverage

Coverage is useful but is not the only measure of quality.

Prioritize coverage for:

Evidence handling
Authentication
Authorization
Parsers
Normalization
Detection
Risk scoring
Correlation
Report generation
Error handling
Security boundaries

Do not write meaningless tests simply to increase a coverage percentage.

19. Test Before Commit

Before committing a feature:

Implement
   ↓
Run focused tests
   ↓
Run relevant integration tests
   ↓
Run security checks
   ↓
Run full test suite where practical
   ↓
Review failures
   ↓
Commit

Never knowingly commit broken tests unless the failure is explicitly documented and intentionally accepted.

20. Test Checklist

Before considering a feature complete:

[ ] Happy path tested
[ ] Invalid input tested
[ ] Failure path tested
[ ] Security implications tested
[ ] Edge cases considered
[ ] Parser fixtures added where applicable
[ ] Integration behavior tested
[ ] Regression test added for bug fixes
[ ] No production data used
[ ] No secrets committed
[ ] Relevant test suite passes
21. Final Principle

The purpose of testing TRACE-X is not simply to prove that the software works.

Testing should provide confidence that:

Evidence
   ↓
Processing
   ↓
Analysis
   ↓
Finding

remains:

Correct
Traceable
Secure
Reproducible
Explainable

When uncertain, prefer adding a test that makes the expected behavior explicit.