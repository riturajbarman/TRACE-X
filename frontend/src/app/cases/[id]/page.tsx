"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, type Case, type Evidence, type Event, type RiskResponse, type ProcessResult, type GraphResponse } from "@/lib/api";
import dynamic from "next/dynamic";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

type Tab = "evidence" | "events" | "detections" | "timeline" | "risk" | "report" | "graph";

function SeverityBadge({ severity }: { severity: string }) {
  const cls: Record<string, string> = {
    CRITICAL: "bg-red-900 text-red-300 border-red-700",
    HIGH: "bg-orange-900 text-orange-300 border-orange-700",
    MEDIUM: "bg-yellow-900 text-yellow-300 border-yellow-700",
    LOW: "bg-blue-900 text-blue-300 border-blue-700",
  };
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded border ${cls[severity.toUpperCase()] ?? "bg-gray-800 text-gray-400 border-gray-700"}`}>
      {severity}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    PENDING:    "bg-gray-800 text-gray-400 border-gray-700",
    PROCESSING: "bg-indigo-900 text-indigo-300 border-indigo-700",
    READY:      "bg-green-900 text-green-300 border-green-700",
    COMPLETED:  "bg-green-900 text-green-300 border-green-700",
    FAILED:     "bg-red-900 text-red-300 border-red-700",
    OPEN:       "bg-green-900 text-green-300 border-green-700",
    CLOSED:     "bg-gray-800 text-gray-400 border-gray-700",
  };
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded border ${map[status.toUpperCase()] ?? "bg-gray-800 text-gray-400 border-gray-700"}`}>
      {status}
    </span>
  );
}

export default function CaseDashboard() {
  const { id } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState<Tab>("evidence");
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [risk, setRisk] = useState<RiskResponse | null>(null);
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [graphFilter, setGraphFilter] = useState<string>("all");
  const [selectedNode, setSelectedNode] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [tabLoading, setTabLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tabError, setTabError] = useState<string | null>(null);

  // Ingest form
  const [showIngest, setShowIngest] = useState(false);
  const [ingestName, setIngestName] = useState("");
  const [ingestSource, setIngestSource] = useState("");
  const [ingestFile, setIngestFile] = useState<File | null>(null);
  const [ingesting, setIngesting] = useState(false);

  // Processing state
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [processResult, setProcessResult] = useState<Record<string, ProcessResult>>({});

  const fileRef = useRef<HTMLInputElement>(null);

  const loadCase = async () => {
    setLoading(true);
    setError(null);
    try {
      const [c, ev] = await Promise.all([api.getCase(id), api.listEvidence()]);
      setCaseData(c);
      setEvidence(ev.filter((e) => e.case_id === id));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadCase(); }, [id]);

  useEffect(() => {
    if (activeTab === "events" || activeTab === "timeline") loadEvents();
    if (activeTab === "risk") loadRisk();
    if (activeTab === "report") loadReport();
    if (activeTab === "graph") loadGraph();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, graphFilter]);

  const loadGraph = async () => {
    setTabLoading(true);
    setTabError(null);
    try {
      setGraph(await api.getCaseGraph(id, graphFilter !== "all" ? { node_types: [graphFilter] } : undefined));
    } catch (e) {
      setTabError((e as Error).message);
    } finally {
      setTabLoading(false);
    }
  };

  const loadEvents = async () => {
    setTabLoading(true);
    setTabError(null);
    try {
      const evts = await api.getCaseTimeline(id);
      setEvents(evts);
    } catch (e) {
      setTabError((e as Error).message);
    } finally {
      setTabLoading(false);
    }
  };

  const loadRisk = async () => {
    setTabLoading(true);
    setTabError(null);
    try {
      setRisk(await api.getCaseRisk(id));
    } catch (e) {
      setTabError((e as Error).message);
    } finally {
      setTabLoading(false);
    }
  };

  const loadReport = async () => {
    setTabLoading(true);
    setTabError(null);
    try {
      setReport(await api.getCaseReport(id));
    } catch (e) {
      setTabError((e as Error).message);
    } finally {
      setTabLoading(false);
    }
  };

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ingestFile || !ingestName.trim()) return;
    setIngesting(true);
    setTabError(null);
    try {
      await api.ingestEvidence(id, ingestName.trim(), ingestFile, ingestSource.trim() || undefined);
      setShowIngest(false);
      setIngestName(""); setIngestSource(""); setIngestFile(null);
      if (fileRef.current) fileRef.current.value = "";
      await loadCase();
    } catch (e) {
      setTabError((e as Error).message);
    } finally {
      setIngesting(false);
    }
  };

  const handleProcess = async (evidenceId: string) => {
    setProcessingId(evidenceId);
    setTabError(null);
    try {
      const result = await api.processEvidence(evidenceId);
      setProcessResult((prev) => ({ ...prev, [evidenceId]: result }));
      await loadCase();
    } catch (e) {
      setTabError((e as Error).message);
    } finally {
      setProcessingId(null);
    }
  };

  const TABS: { key: Tab; label: string }[] = [
    { key: "evidence", label: "Evidence" },
    { key: "events", label: "Events" },
    { key: "timeline", label: "Timeline" },
    { key: "risk", label: "Risk" },
    { key: "report", label: "Report" },
    { key: "graph", label: "Graph" },
  ];

  if (loading) return <div className="text-gray-500 text-sm">Loading case…</div>;
  if (error) return <div className="text-red-400 text-sm">Error: {error}</div>;
  if (!caseData) return null;

  return (
    <div>
      {/* Breadcrumb */}
      <div className="text-sm text-gray-500 mb-4">
        <Link href="/" className="hover:text-gray-300 transition">Cases</Link>
        <span className="mx-2">/</span>
        <span className="text-gray-300">{caseData.title}</span>
      </div>

      {/* Case Header */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 id="case-title" className="text-xl font-bold text-gray-100">{caseData.title}</h1>
            {caseData.description && <p className="text-gray-500 text-sm mt-1">{caseData.description}</p>}
            <p className="text-xs text-gray-600 mt-2">
              {caseData.created_by && <span className="mr-3">Investigator: {caseData.created_by}</span>}
              Created: {new Date(caseData.created_at).toLocaleString()}
            </p>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <StatusBadge status={caseData.status} />
            <span className="text-xs text-gray-600 font-mono">{caseData.id.slice(0, 8)}…</span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-800 mb-6 gap-1">
        {TABS.map((t) => (
          <button
            key={t.key}
            id={`tab-${t.key}`}
            onClick={() => setActiveTab(t.key)}
            className={`px-4 py-2 text-sm font-medium transition rounded-t-lg ${
              activeTab === t.key
                ? "text-indigo-300 border-b-2 border-indigo-500 bg-gray-900"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tabError && (
        <div id="tab-error" className="mb-4 p-3 bg-red-950 border border-red-800 rounded-lg text-red-300 text-sm">
          {tabError}
        </div>
      )}

      {/* Evidence Tab */}
      {activeTab === "evidence" && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">Evidence ({evidence.length})</h2>
            <button
              id="btn-ingest-evidence"
              onClick={() => setShowIngest((v) => !v)}
              className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium px-3 py-1.5 rounded-lg transition"
            >
              + Ingest Evidence
            </button>
          </div>

          {showIngest && (
            <form onSubmit={handleIngest} className="mb-5 bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Ingest Evidence File</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Name *</label>
                  <input id="input-evidence-name" className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500" placeholder="e.g. disk.dd" value={ingestName} onChange={(e) => setIngestName(e.target.value)} required />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Source</label>
                  <input id="input-evidence-source" className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500" placeholder="e.g. local, usb, network" value={ingestSource} onChange={(e) => setIngestSource(e.target.value)} />
                </div>
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">File *</label>
                <input id="input-evidence-file" ref={fileRef} type="file" className="w-full text-sm text-gray-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:bg-gray-700 file:text-gray-200 file:text-xs hover:file:bg-gray-600 file:transition" onChange={(e) => setIngestFile(e.target.files?.[0] ?? null)} required />
              </div>
              <div className="flex gap-3">
                <button id="btn-submit-ingest" type="submit" disabled={ingesting} className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium px-3 py-1.5 rounded-lg transition">
                  {ingesting ? "Ingesting…" : "Ingest"}
                </button>
                <button type="button" onClick={() => setShowIngest(false)} className="text-gray-400 hover:text-gray-200 text-xs px-3 py-1.5 transition">Cancel</button>
              </div>
            </form>
          )}

          {evidence.length === 0 ? (
            <div className="text-center py-12 text-gray-600 text-sm">No evidence ingested yet.</div>
          ) : (
            <div className="space-y-3">
              {evidence.map((ev) => (
                <div key={ev.id} id={`evidence-${ev.id}`} className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-sm text-gray-200">{ev.name}</span>
                      <StatusBadge status={ev.status} />
                    </div>
                    <p className="text-xs text-gray-600 font-mono truncate">SHA-256: {ev.sha256}</p>
                    {processResult[ev.id] && (
                      <p className="text-xs text-green-400 mt-1">
                        ✓ {processResult[ev.id].extracted_artifacts} artifacts · {processResult[ev.id].events_created} events · {processResult[ev.id].detections_created} detections
                      </p>
                    )}
                  </div>
                  <div className="flex gap-2 shrink-0">
                    {(ev.status === "PENDING" || ev.status === "FAILED") && (
                      <button
                        id={`btn-process-${ev.id}`}
                        onClick={() => handleProcess(ev.id)}
                        disabled={processingId === ev.id}
                        className="bg-indigo-700 hover:bg-indigo-600 disabled:opacity-50 text-white text-xs font-medium px-3 py-1.5 rounded-lg transition"
                      >
                        {processingId === ev.id ? "Processing…" : "Process"}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Events Tab */}
      {activeTab === "events" && (
        <div>
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-4">Raw Events</h2>
          {tabLoading ? (
            <div className="text-gray-500 text-sm">Loading events…</div>
          ) : events.length === 0 ? (
            <div className="text-center py-12 text-gray-600 text-sm">No events yet. Process evidence to generate events.</div>
          ) : (
            <div className="space-y-2">
              {events.slice(0, 200).map((ev) => (
                <div key={ev.id} id={`event-${ev.id}`} className="bg-gray-900 border border-gray-800 rounded-lg p-3 text-xs font-mono">
                  <div className="flex items-center gap-3 mb-1">
                    <span className="text-indigo-400">{new Date(ev.timestamp).toISOString()}</span>
                    <span className="text-gray-400">{ev.event_type}</span>
                    <span className="text-gray-600">{ev.source}</span>
                  </div>
                  <div className="text-gray-500 truncate">{JSON.stringify(ev.data)}</div>
                </div>
              ))}
              {events.length > 200 && (
                <p className="text-xs text-gray-600 text-center py-2">Showing 200 of {events.length} events</p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Timeline Tab */}
      {activeTab === "timeline" && (
        <div>
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-4">Timeline</h2>
          {tabLoading ? (
            <div className="text-gray-500 text-sm">Loading timeline…</div>
          ) : events.length === 0 ? (
            <div className="text-center py-12 text-gray-600 text-sm">No events on timeline. Process evidence to populate timeline.</div>
          ) : (
            <div className="relative pl-6 border-l border-gray-800 space-y-4">
              {events.slice(0, 200).map((ev) => (
                <div key={ev.id} id={`timeline-${ev.id}`} className="relative">
                  <div className="absolute -left-[25px] top-2 w-2.5 h-2.5 rounded-full bg-indigo-600 border-2 border-gray-950" />
                  <div className="bg-gray-900 border border-gray-800 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-xs text-indigo-400 font-mono">{new Date(ev.timestamp).toISOString()}</span>
                      <span className="text-xs text-gray-400 bg-gray-800 px-1.5 py-0.5 rounded">{ev.event_type}</span>
                      <span className="text-xs text-gray-600">{ev.source}</span>
                    </div>
                    <div className="text-xs text-gray-500 font-mono truncate">{JSON.stringify(ev.data)}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Risk Tab */}
      {activeTab === "risk" && (
        <div>
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-4">Risk Assessment</h2>
          {tabLoading ? (
            <div className="text-gray-500 text-sm">Loading risk…</div>
          ) : !risk ? null : (
            <div className="space-y-4">
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 flex items-center gap-6">
                <div className="text-center">
                  <div
                    id="risk-score"
                    className={`text-5xl font-bold ${
                      risk.risk_level === "CRITICAL" ? "text-red-400" :
                      risk.risk_level === "HIGH" ? "text-orange-400" :
                      risk.risk_level === "MEDIUM" ? "text-yellow-400" :
                      risk.risk_level === "LOW" ? "text-blue-400" : "text-gray-500"
                    }`}
                  >
                    {risk.risk_score}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">/ 100</div>
                </div>
                <div>
                  <div id="risk-level" className={`text-lg font-semibold mb-1 ${
                    risk.risk_level === "CRITICAL" ? "text-red-400" :
                    risk.risk_level === "HIGH" ? "text-orange-400" :
                    risk.risk_level === "MEDIUM" ? "text-yellow-400" :
                    risk.risk_level === "LOW" ? "text-blue-400" : "text-gray-500"
                  }`}>{risk.risk_level}</div>
                  <p className="text-sm text-gray-400">{risk.explanation}</p>
                </div>
              </div>

              {risk.contributing_signals.length > 0 && (
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                  <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Contributing Signals</h3>
                  <div className="space-y-2">
                    {risk.contributing_signals.map((sig, i) => (
                      <div key={i} className="flex items-center justify-between text-sm border-b border-gray-800 pb-2 last:border-0 last:pb-0">
                        <div>
                          <span className="text-gray-300">{sig.description}</span>
                          <span className="ml-2 text-xs text-gray-600">{sig.source}</span>
                        </div>
                        <span className="text-indigo-400 font-mono font-semibold">+{sig.score}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Report Tab */}
      {activeTab === "report" && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">Case Report (JSON)</h2>
            {report && (
              <button
                id="btn-download-report"
                onClick={() => {
                  const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url; a.download = `tracex-report-${id}.json`; a.click();
                  URL.revokeObjectURL(url);
                }}
                className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium px-3 py-1.5 rounded-lg transition"
              >
                ↓ Download JSON
              </button>
            )}
          </div>
          {tabLoading ? (
            <div className="text-gray-500 text-sm">Generating report…</div>
          ) : !report ? null : (
            <pre
              id="report-json"
              className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-xs text-gray-400 font-mono overflow-auto max-h-[60vh]"
            >
              {JSON.stringify(report, null, 2)}
            </pre>
          )}
        </div>
      )}
      {/* Graph Tab */}
      {activeTab === "graph" && (
        <div className="flex gap-6 h-[70vh]">
          {/* Main Graph Area */}
          <div className="flex-1 bg-gray-900 border border-gray-800 rounded-xl relative overflow-hidden">
            {tabLoading ? (
              <div className="absolute inset-0 flex items-center justify-center text-gray-500 text-sm">
                Loading graph...
              </div>
            ) : !graph || graph.nodes.length === 0 ? (
              <div className="absolute inset-0 flex items-center justify-center text-gray-500 text-sm">
                No graph data available.
              </div>
            ) : (
              <ForceGraph2D
                graphData={{
                  nodes: graph.nodes.map(n => ({ ...n, id: n.id, val: n.type === 'incident' ? 5 : 2 })),
                  links: graph.edges.map(e => ({ source: e.source, target: e.target, name: e.relationship }))
                }}
                nodeLabel="label"
                nodeColor={(node: any) => {
                  switch (node.type) {
                    case "event": return "#6366f1"; // indigo
                    case "detection": return "#ef4444"; // red
                    case "ioc": return "#f59e0b"; // amber
                    case "incident": return "#a855f7"; // purple
                    default: return "#9ca3af"; // gray
                  }
                }}
                nodeRelSize={4}
                linkColor={() => "#4b5563"}
                linkDirectionalArrowLength={3.5}
                linkDirectionalArrowRelPos={1}
                onNodeClick={(node) => setSelectedNode(node)}
                backgroundColor="#111827"
              />
            )}

            {/* Filter Overlay */}
            <div className="absolute top-4 left-4 bg-gray-800/80 backdrop-blur border border-gray-700 rounded-lg p-2 flex gap-2">
              <select
                value={graphFilter}
                onChange={(e) => setGraphFilter(e.target.value)}
                className="bg-gray-900 border border-gray-700 text-sm text-gray-300 rounded px-2 py-1 outline-none focus:border-indigo-500"
              >
                <option value="all">All Node Types</option>
                <option value="event">Events Only</option>
                <option value="detection">Detections Only</option>
                <option value="ioc">IOCs Only</option>
                <option value="incident">Incidents Only</option>
              </select>
            </div>
          </div>

          {/* Node Detail Panel */}
          {selectedNode && (
            <div className="w-80 bg-gray-900 border border-gray-800 rounded-xl p-5 overflow-y-auto">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-200">Node Details</h3>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="text-gray-500 hover:text-gray-300 transition"
                >
                  ×
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Type</div>
                  <span className={`text-xs px-2 py-1 rounded bg-gray-800 ${
                    selectedNode.type === "event" ? "text-indigo-400" :
                    selectedNode.type === "detection" ? "text-red-400" :
                    selectedNode.type === "ioc" ? "text-amber-400" :
                    selectedNode.type === "incident" ? "text-purple-400" : "text-gray-400"
                  }`}>
                    {selectedNode.type}
                  </span>
                </div>

                <div>
                  <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Label</div>
                  <div className="text-sm text-gray-300 break-words">{selectedNode.label}</div>
                </div>

                {selectedNode.severity && (
                  <div>
                    <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Severity</div>
                    <SeverityBadge severity={selectedNode.severity} />
                  </div>
                )}

                {selectedNode.timestamp && (
                  <div>
                    <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Timestamp</div>
                    <div className="text-xs text-gray-400 font-mono">{selectedNode.timestamp}</div>
                  </div>
                )}

                {selectedNode.evidence_id && (
                  <div>
                    <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Provenance (Evidence)</div>
                    <div className="text-xs text-gray-400 font-mono break-all">{selectedNode.evidence_id}</div>
                  </div>
                )}

                {selectedNode.data && Object.keys(selectedNode.data).length > 0 && (
                  <div>
                    <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Data</div>
                    <pre className="text-[10px] text-gray-400 font-mono bg-gray-950 p-2 rounded border border-gray-800 overflow-x-auto">
                      {JSON.stringify(selectedNode.data, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
