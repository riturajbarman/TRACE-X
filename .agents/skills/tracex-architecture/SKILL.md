---
name: tracex-architecture
description: Use this skill when designing, reviewing, or changing TRACE-X architecture, interfaces, data flow, domain boundaries, or major technical decisions.
---

# TRACE-X Architecture Skill

## Purpose

Use this skill when a task affects the architecture or structure of TRACE-X.

The goal is to preserve a modular, secure, explainable and maintainable
architecture.

---

## Required Context

Before making an architectural decision, read:

1. BRAIN.md
2. TRACESPEC.md
3. PIPELINE.md
4. AGENTS.md
5. STATUS.md
6. Relevant existing implementation

Do not make architectural decisions from the task prompt alone.

---

## Architecture Principles

TRACE-X follows these principles:

- Evidence first.
- Automation second.
- AI last.
- Raw evidence is untrusted.
- Original evidence is immutable.
- Derived objects preserve provenance.
- Trusted processing consumes validated structured data.
- Investigator-facing systems consume trusted data.
- Important findings must be explainable.
- Components should remain modular.
- Prefer simple architecture before complex architecture.
- Do not introduce complexity without a measurable reason.

---

## Trust Zones

Maintain the three-zone architecture:

```text
UNTRUSTED
Evidence
   ↓
Validation
   ↓
Hashing
   ↓
Sandboxed Extraction
        ↓
TRUSTED
Normalization
   ↓
Event Store
   ↓
Detection / Analysis
   ↓
Correlation
   ↓
Timeline / Risk
        ↓
INVESTIGATOR
Dashboard / AI / Reports
```

Never casually move responsibilities across these boundaries.

---

## Before Proposing a Change

Determine:

1. Which component owns the behavior?
2. What are its inputs?
3. What are its outputs?
4. What trust zone does it belong to?
5. What data model does it use?
6. What existing component already handles something similar?
7. What happens if it fails?
8. How will it be tested?
9. What security implications exist?
10. Does the change require a specification update?

---

## Major Architecture Changes

Treat the following as major changes:

- Changing the Event model
- Changing Evidence semantics
- Changing evidence storage
- Changing trust boundaries
- Replacing major frameworks
- Introducing distributed processing
- Making an external AI provider mandatory
- Changing the core pipeline
- Changing database strategy
- Changing parser execution architecture

For a major change:

1. Explain the current problem.
2. Explain the proposed solution.
3. Explain alternatives.
4. Explain tradeoffs.
5. Identify affected documents.
6. Obtain project-owner approval when required.
7. Update documentation before implementation.

---

## Modularity Rules

Prefer:

```text
Focused component
       ↓
Explicit interface
       ↓
Testable behavior
```

Avoid:

- Giant modules
- Circular dependencies
- Hidden global state
- Duplicate business logic
- Unrelated responsibilities in one component
- UI components containing core forensic logic
- Direct database access from unrelated layers

---

## Data Flow Rules

For any new component, explicitly define:

```text
Input
  ↓
Validation
  ↓
Processing
  ↓
Output
  ↓
Provenance
  ↓
Failure state
```

A component is not architecturally complete if its failure behavior is
undefined.

---

## Dependency Rules

Before adding a dependency:

- Check whether the project already provides equivalent functionality.
- Check whether the dependency is necessary.
- Check maintenance/security quality.
- Consider project complexity.
- Consider licensing.
- Consider reproducibility.

Do not add dependencies because an AI-generated example happens to use
them.

---

## Architecture Review Checklist

Before accepting an architectural change:

```text
[ ] Fits TRACESPEC
[ ] Fits PIPELINE
[ ] Fits BRAIN
[ ] Does not violate AGENTS
[ ] Correct trust zone
[ ] Clear inputs/outputs
[ ] Clear ownership
[ ] Failure behavior defined
[ ] Provenance preserved
[ ] Security considered
[ ] Testing strategy defined
[ ] Documentation impact identified
[ ] No unnecessary complexity
```

---

## Final Rule

Do not optimize the architecture for how impressive it sounds.

Optimize for:

```text
Correctness
Security
Explainability
Maintainability
Testability
Measurable performance
```