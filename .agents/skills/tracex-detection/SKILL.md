---
name: tracex-detection
description: Use this skill when designing, implementing, reviewing, or modifying TRACE-X IOC detection, detection rules, behavioral analysis, correlation, risk scoring, anomaly detection, MITRE ATT&CK mapping, or investigation findings.
---

# TRACE-X Detection Skill

## Purpose

Use this skill whenever TRACE-X needs to determine whether observed forensic
data represents suspicious, malicious, anomalous, or otherwise significant
activity.

The goal is to produce:

- Evidence-backed detections
- Explainable findings
- Reproducible results
- Traceable risk scores
- Useful investigation context
- Minimal false confidence

Detection must be based on observable evidence.

---

# 1. Detection Principles

TRACE-X follows these principles:

- Evidence before interpretation.
- Deterministic detection before AI interpretation.
- Every finding must have supporting evidence.
- Detection and evidence are different concepts.
- A suspicious indicator is not automatically proof of compromise.
- Confidence must reflect available evidence.
- Missing evidence must not be treated as evidence of absence.
- Detection rules should be explainable.
- Detection results should be reproducible.
- AI may assist analysis but must not silently replace deterministic detection.

---

# 2. Detection Pipeline

Detection should conceptually follow:

```text
Raw Evidence
     ↓
Artifact Extraction
     ↓
Normalization
     ↓
Events
     ↓
IOC Detection
     ↓
Rule Detection
     ↓
Behavioral Analysis
     ↓
Correlation
     ↓
Risk Scoring
     ↓
Investigation Finding

Do not skip directly from raw evidence to an unsupported conclusion.

3. Detection Layers

TRACE-X should separate detection into multiple layers.

Layer 1
IOC Detection

Layer 2
Rule Detection

Layer 3
Behavioral / Anomaly Detection

Layer 4
Correlation

Layer 5
Risk Scoring

Each layer should have a clear responsibility.

4. IOC Detection

IOC detection identifies known indicators.

Examples:

IP address
Domain
URL
File hash
Email address
File path
Registry key
Process name
Command pattern

An IOC finding should record:

IOC value
IOC type
Source artifact
Source event
Detection method
Confidence
Severity
Timestamp where applicable

Never create an IOC finding without identifying where the IOC came from.

5. IOC Normalization

Normalize indicators before matching where appropriate.

Examples:

Domain
domain.com
DOMAIN.COM

may represent the same logical indicator.

Similarly consider:

Case normalization
IP representation
URL normalization
Hash normalization
Whitespace normalization

Do not normalize in ways that destroy forensic meaning.

Preserve the original observed value.

Conceptually:

Original Value
      ↓
Normalized Value
      ↓
Matching

Both should remain available where useful.

6. IOC Confidence

IOC matches must not automatically be considered malicious.

Consider:

Known malicious IOC
      ↓
High confidence

Unknown IOC
      ↓
Low confidence

Common legitimate infrastructure
      ↓
Potentially benign

Confidence should reflect the quality of the underlying intelligence.

7. Rule Engine

Rules should describe observable conditions.

Example:

IF

PowerShell execution
+
Encoded command
+
External network connection

THEN

Potential suspicious execution

Rules should have:

Rule ID
Name
Description
Version
Severity
Conditions
Required evidence
Output finding
Explanation

Example:

DET-001
Suspicious PowerShell Execution
Version: 1.0
Severity: HIGH
8. Rule Design

Prefer simple composable rules.

Avoid rules that contain large amounts of hidden logic.

A rule should answer:

What did we observe?

and:

Why does this combination matter?

Do not write:

IF AI says suspicious
THEN mark malicious

Detection rules must be based on structured evidence.

9. Rule Explainability

Every triggered rule should produce an explanation.

Example:

Rule: DET-017

Finding:
Potential persistence mechanism

Observed evidence:

1. Registry startup key modified
2. New executable created
3. Executable path is unusual

Reason:
The observed combination matches a known persistence pattern.

The investigator must be able to inspect the supporting evidence.

10. Severity

Severity represents the potential importance of a detection.

Example:

LOW
MEDIUM
HIGH
CRITICAL

Severity should not be arbitrary.

Consider:

Potential impact
Confidence
Evidence quality
Known maliciousness
Persistence
Credential access
Network behavior
Data access
Privilege escalation
11. Confidence vs Severity

Do not confuse confidence and severity.

Example:

Severity: CRITICAL
Confidence: LOW

could mean:

If this behavior is confirmed, it could be extremely serious, but the
current evidence is weak.

Similarly:

Severity: MEDIUM
Confidence: HIGH

could mean:

We are very confident the event occurred, but its impact appears limited.

Both dimensions should remain separate.

12. Behavioral Detection

Behavioral detection looks for unusual combinations or patterns.

Examples:

Rare process execution
Unusual execution time
Unexpected parent-child process relationship
Unusual network destination
Sudden file creation
Unusual registry modification
Abnormal login behavior
Large data access

Behavioral detection should describe what makes the behavior unusual.

Avoid vague findings such as:

AI says behavior is suspicious.

Prefer:

Process executed at an unusual time and contacted an uncommon external
destination compared with the available baseline.
13. Baseline Awareness

When a baseline is available, distinguish between:

Normal
Unusual
Suspicious
Malicious

These are not equivalent.

An unusual event is not automatically malicious.

Example:

First-time software execution
        ↓
UNUSUAL

does not necessarily mean:

MALICIOUS
14. Anomaly Detection

Machine-learning anomaly detection may be used where appropriate.

Suitable early approaches may include:

Isolation Forest
Statistical thresholds
Frequency analysis
Clustering

The model should produce an anomaly signal rather than an unsupported
malware verdict.

Example:

Anomaly Score: 0.91

Reasons:

- Rare process
- Unusual execution time
- Uncommon network destination
- New executable
15. ML Feature Design

Features should be derived from structured events.

Potential features:

Process frequency
Network connection count
Unique destination count
PowerShell execution count
New executable count
Registry modification count
Login frequency
Execution time
File access frequency
Rare command frequency

Document the meaning of every important feature.

Do not feed arbitrary raw evidence into an ML model without understanding
what the model is learning.

16. ML Limitations

ML results must be treated as probabilistic.

Do not say:

Anomaly score 0.91
=
91% probability of malware

unless the model has actually been calibrated and validated for that
interpretation.

Prefer:

Behavioral anomaly score: 0.91

and explain what the score means.

17. Correlation

Correlation combines related observations.

Example:

PowerShell
      ↓
Encoded command
      ↓
File creation
      ↓
External network connection
      ↓
Persistence

The correlation engine may combine these into:

Potential compromise sequence

Correlation should preserve the individual observations.

Never replace the underlying evidence with only the final conclusion.

18. Temporal Correlation

Time is an important correlation signal.

Consider:

Event A
10:21:04

Event B
10:21:12

Event C
10:21:17

These may be more strongly related than events occurring days apart.

Correlation logic should define its time window explicitly.

Example:

Within 5 minutes

Do not use arbitrary time windows without documenting the reason.

19. Entity Correlation

Useful entities include:

User
Host
Process
File
Hash
IP
Domain
URL
Registry Key
Event

Relationships can form:

User
 ↓
Process
 ↓
File
 ↓
Hash
 ↓
Network Connection
 ↓
IP

These relationships can support investigation graphs and incident stories.

20. MITRE ATT&CK Mapping

Where appropriate, map detections to MITRE ATT&CK techniques.

Example:

PowerShell
      ↓
T1059.001
PowerShell

A mapping should only be added when the observed behavior supports it.

Do not map every suspicious event to an ATT&CK technique simply to make
the dashboard look complete.

Record:

Technique ID
Technique name
Supporting detection
Evidence
Confidence
21. Finding Model

A detection finding should conceptually contain:

Finding
├── finding_id
├── title
├── description
├── severity
├── confidence
├── detection_type
├── rule_id
├── evidence references
├── event references
├── IOC references
├── ATT&CK mapping
├── timestamps
└── explanation

The exact implementation must follow the project's canonical data model.

22. Evidence References

Every important finding should point back to evidence.

Example:

Finding
  ↓
Event #18291
  ↓
Artifact #421
  ↓
Evidence #CASE-001

The investigator must be able to navigate from:

Finding

to:

Supporting Evidence
23. False Positives

Detection systems must expect false positives.

Do not hide them.

Where appropriate, allow investigators to:

Confirm
Dismiss
Mark benign
Add context

A dismissed detection should remain auditable.

Do not permanently delete the original detection without a documented reason.

24. False Negative Awareness

The absence of a detection does not prove the absence of malicious activity.

For example:

No IOC detected

does not mean:

No compromise

The UI and reports should avoid making unsupported claims.

25. Risk Scoring

Risk scoring combines multiple signals.

A conceptual score may consider:

IOC severity
Rule severity
Behavior anomaly
Correlation strength
Evidence confidence
Asset criticality

Example:

IOC severity        25%
Rule detections     25%
Behavior anomaly    20%
Correlation          20%
Asset criticality   10%

The exact weighting must be documented and configurable.

Do not hide scoring logic.

26. Explainable Risk

A risk score must have supporting factors.

Example:

Risk Score: 87 / 100

Factors:

+25 Suspicious IOC
+20 PowerShell anomaly
+18 Persistence mechanism
+14 External C2-like connection
+10 Credential access

The investigator should understand how the score was produced.

27. Risk Score Limitations

A risk score is a prioritization mechanism.

It is not proof of compromise.

Avoid language such as:

Risk Score = 95
Therefore system is definitely compromised.

Prefer:

High-priority investigation based on correlated evidence.
28. AI-Assisted Detection

AI may assist with:

Finding summaries
Natural-language explanations
Event clustering suggestions
Investigation questions
Attack-story generation
Report drafting
Analyst assistance

AI should not silently invent:

Evidence
IOC values
Timestamps
Events
Attack techniques
Confidence
Risk factors

AI-generated statements must be grounded in structured findings.

29. AI Evidence Grounding

Prefer:

Structured Findings
       ↓
Relevant Evidence
       ↓
AI Context
       ↓
AI Explanation

Avoid:

Raw Evidence
       ↓
LLM
       ↓
"Malware detected"

The AI should explain existing evidence rather than create unsupported
forensic facts.

30. Detection Ordering

Prefer this order:

IOC
 ↓
Rules
 ↓
Behavior
 ↓
Correlation
 ↓
Risk
 ↓
AI Explanation

AI should normally be the final interpretation layer.

31. Detection Versioning

Detection rules and models can change.

Record versions for reproducibility.

For important findings preserve:

Rule Version
Model Version
Schema Version
Detection Configuration

A future rule update should not make an old investigation impossible to
understand.

32. Detection Testing

Every detection should have tests.

Test:

[ ] Positive case
[ ] Negative case
[ ] Edge case
[ ] Missing data
[ ] Conflicting data
[ ] Malformed data
[ ] Multiple matching events
[ ] Duplicate events
[ ] Timestamp boundary

For rules, use known fixtures.

Example:

Fixture
   ↓
Events
   ↓
Detection Rule
   ↓
Expected Finding
33. Detection Quality

Measure detection quality where practical.

Useful metrics include:

True Positives
False Positives
False Negatives
Precision
Recall
Detection latency

Do not optimize only for the number of detections.

A system that generates thousands of useless alerts is not necessarily
better.

34. Detection Review Checklist

Before accepting a new detection:

[ ] Evidence source identified
[ ] Detection purpose documented
[ ] Conditions defined
[ ] Severity defined
[ ] Confidence behavior defined
[ ] Explanation available
[ ] Provenance preserved
[ ] False positive considered
[ ] Negative case tested
[ ] ATT&CK mapping justified where applicable
[ ] Version recorded
[ ] Risk impact considered
[ ] AI dependency avoided unless necessary
35. What This Skill Must Prevent

This skill exists specifically to prevent:

Unsupported malware claims
AI-only detections
Unexplainable risk scores
Detection without evidence
Lost provenance
Confusing anomaly with maliciousness
Confusing severity with confidence
Arbitrary scoring
False certainty
Unjustified MITRE ATT&CK mappings
Hidden detection logic
Detection rules without tests
Silent deletion of false positives
Treating "no detection" as "no compromise"
36. Final Principle

TRACE-X detection should answer:

"What did we observe, why is it significant, how confident are we, and
what evidence supports the finding?"

The correct chain is:

Evidence
   ↓
Observation
   ↓
Detection
   ↓
Correlation
   ↓
Risk
   ↓
Explanation

Never reverse this chain.

Do not start with a conclusion and search for evidence to support it.