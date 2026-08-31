// API Client — all calls to the TRACE-X FastAPI backend

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Case {
  id: string;
  title: string;
  description: string | null;
  status: string;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface CaseCreate {
  title: string;
  description?: string;
  created_by?: string;
}

export interface Evidence {
  id: string;
  case_id: string;
  name: string;
  description: string | null;
  status: string;
  sha256: string;
  source: string | null;
  size_bytes: number;
  created_at: string;
}

export interface Event {
  id: string;
  artifact_id: string | null;
  evidence_id: string | null;
  case_id: string;
  event_type: string;
  source: string;
  timestamp: string;
  timestamp_desc: string | null;
  data: Record<string, unknown>;
  created_at: string;
}

export interface Detection {
  id: string;
  case_id: string;
  event_id: string;
  detection_type: string;
  rule_id: string | null;
  severity: string;
  confidence: number;
  created_at: string;
}

export interface IOC {
  id: string;
  case_id: string;
  event_id: string;
  ioc_type: string;
  value: string;
  severity: string;
  confidence: number;
  created_at: string;
}

export interface Incident {
  id: string;
  case_id: string;
  title: string;
  severity: string;
  confidence: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface AuditEvent {
  id: string;
  timestamp: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  outcome: string;
  details: Record<string, unknown> | null;
}

// Phase 13 — Investigator Dashboard. Read-only aggregate counts computed
// server-side from already-persisted data (no client-side recomputation).
export interface CaseSummary extends Case {
  evidence_count: number;
  event_count: number;
  detection_count: number;
  ioc_count: number;
  incident_count: number;
  failed_evidence_count: number;
}

export interface RiskSignal {
  source: string;
  description: string;
  score: number;
  detection_id: string | null;
  ioc_id: string | null;
}

export interface RiskResponse {
  case_id: string;
  risk_score: number;
  risk_level: string;
  explanation: string;
  contributing_signals: RiskSignal[];
}

export interface ProcessResult {
  status: string;
  extracted_artifacts: number;
  events_created: number;
  detections_created: number;
}

export interface GraphNode {
  id: string;
  type: string;
  label: string;
  evidence_id: string | null;
  case_id: string | null;
  timestamp: string | null;
  severity: string | null;
  data: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
  label: string | null;
}

export interface GraphResponse {
  case_id: string;
  node_count: number;
  edge_count: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// Phase 11 — AI Investigation Assistant.
// Deliberately structurally separate from RiskResponse / GraphResponse /
// the report JSON — an assistant response can never be mistaken for a
// deterministic TRACE-X finding.
//
// Phase 12 — "external_knowledge" claims carry `knowledge_refs` (external
// citations, e.g. MITRE ATT&CK) instead of `refs` (validated TRACE-X case
// object ids). The two are never mixed by the backend — a knowledge
// citation can never appear in `refs`, and a case object id can never
// appear as a knowledge citation.
export type AssistantClaimType = "observed" | "inference" | "recommendation" | "external_knowledge";
export type AssistantGroundingStatus = "ok" | "partial" | "unavailable";

export interface KnowledgeCitation {
  source_id: string;
  source_type: string;
  document_id: string;
  version: string;
  title: string;
  reference: string;
  retrieval_method: "deterministic_lookup";
}

export interface AssistantClaim {
  text: string;
  type: AssistantClaimType;
  refs: string[];
  knowledge_refs: KnowledgeCitation[];
}

export interface AssistantQueryResponse {
  case_id: string;
  answer: string;
  claims: AssistantClaim[];
  grounding_status: AssistantGroundingStatus;
  provider: string;
  model: string | null;
  warnings: string[];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail ?? resp.statusText);
  }
  return resp.json() as Promise<T>;
}

export const api = {
  // Cases
  listCases: () => request<Case[]>("/cases"),
  createCase: (body: CaseCreate) =>
    request<Case>("/cases", { method: "POST", body: JSON.stringify(body) }),
  getCase: (id: string) => request<Case>(`/cases/${id}`),
  getCaseRisk: (id: string) => request<RiskResponse>(`/cases/${id}/risk`),
  getCaseTimeline: (id: string, params?: { severity?: string; source?: string }) => {
    const qs = params
      ? "?" + new URLSearchParams(Object.entries(params).filter(([, v]) => v != null) as string[][]).toString()
      : "";
    return request<Event[]>(`/cases/${id}/timeline${qs}`);
  },
  getCaseReport: (id: string) => request<Record<string, unknown>>(`/cases/${id}/report`),
  getCaseGraph: (id: string, params?: { node_types?: string[], include_shared_entities?: boolean }) => {
    let qs = "";
    if (params) {
      const parts: string[] = [];
      if (params.node_types) {
        params.node_types.forEach(t => parts.push(`node_types=${t}`));
      }
      if (params.include_shared_entities !== undefined) {
        parts.push(`include_shared_entities=${params.include_shared_entities}`);
      }
      if (parts.length > 0) qs = "?" + parts.join("&");
    }
    return request<GraphResponse>(`/cases/${id}/graph${qs}`);
  },
  queryCaseAssistant: (id: string, question: string) =>
    request<AssistantQueryResponse>(`/cases/${id}/assistant/query`, {
      method: "POST",
      body: JSON.stringify({ question }),
    }),

  // Phase 13 — Investigator Dashboard. All read-only, case-scoped.
  getCaseSummary: (id: string) => request<CaseSummary>(`/cases/${id}/summary`),
  getCaseDetections: (id: string) => request<Detection[]>(`/cases/${id}/detections`),
  getCaseIOCs: (id: string) => request<IOC[]>(`/cases/${id}/iocs`),
  getCaseIncidents: (id: string) => request<Incident[]>(`/cases/${id}/incidents`),
  getCaseAuditLog: (id: string) => request<AuditEvent[]>(`/cases/${id}/audit`),

  // Evidence
  ingestEvidence: (caseId: string, name: string, file: File, source?: string) => {
    const form = new FormData();
    form.set("case_id", caseId);
    form.set("name", name);
    if (source) form.set("source", source);
    form.set("file", file);
    return fetch(`${BASE_URL}/evidence/ingest`, { method: "POST", body: form }).then(async (r) => {
      if (!r.ok) {
        const e = await r.json().catch(() => ({ detail: r.statusText }));
        throw new Error(e.detail ?? r.statusText);
      }
      return r.json() as Promise<Evidence>;
    });
  },
  listEvidence: () => request<Evidence[]>("/evidence"),
  processEvidence: (evidenceId: string) =>
    request<ProcessResult>(`/evidence/${evidenceId}/process`, { method: "POST" }),
};
