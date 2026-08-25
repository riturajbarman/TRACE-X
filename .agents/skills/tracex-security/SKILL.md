---
name: tracex-security
description: Use this skill when designing, implementing, reviewing, or modifying TRACE-X security controls, authentication, authorization, evidence access, APIs, secrets, containers, storage, network boundaries, AI integrations, or deployment.
---

# TRACE-X Security Skill

## Purpose

Use this skill whenever a change affects the security of TRACE-X.

The goal is to protect:

- Evidence
- Investigator accounts
- Case data
- Derived forensic artifacts
- Detection results
- Reports
- Infrastructure
- APIs
- Processing workers
- AI integrations

Security must be designed into the system rather than added after implementation.

---

# 1. Security Principles

TRACE-X follows these principles:

- Least privilege
- Defense in depth
- Secure by default
- Explicit authorization
- Strong authentication
- Minimize trust
- Validate untrusted input
- Fail safely
- Preserve auditability
- Protect evidence integrity
- Never expose secrets
- Never trust client-side security controls
- Treat AI output as untrusted
- Prefer deterministic security controls over AI decisions

---

# 2. Security Boundary

The system should conceptually maintain:

```text
Internet / User
      ↓
Frontend
      ↓
API Boundary
      ↓
Application Services
      ↓
Trusted Data
      ↓
Analysis Services
      ↓
Sandboxed Evidence Processing
      ↓
Original Evidence