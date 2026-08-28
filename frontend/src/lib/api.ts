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
