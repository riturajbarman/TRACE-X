"use client";

import { useEffect, useState } from "react";
import { api, type Case } from "@/lib/api";
import Link from "next/link";

export default function CasesPage() {
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create case form state
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [createdBy, setCreatedBy] = useState("");

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listCases();
      setCases(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setCreating(true);
    setError(null);
    try {
      await api.createCase({ title: title.trim(), description: description.trim() || undefined, created_by: createdBy.trim() || undefined });
      setTitle("");
      setDescription("");
      setCreatedBy("");
      setShowForm(false);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Cases</h1>
          <p className="text-gray-500 text-sm mt-1">All active investigation cases</p>
        </div>
        <button
          id="btn-new-case"
          onClick={() => setShowForm((v) => !v)}
          className="bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition"
        >
          + New Case
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={handleCreate}
          className="mb-6 bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4"
        >
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">Create Case</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Title *</label>
              <input
                id="input-case-title"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500"
                placeholder="Case title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Created By</label>
              <input
                id="input-case-created-by"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500"
                placeholder="Investigator name"
                value={createdBy}
                onChange={(e) => setCreatedBy(e.target.value)}
              />
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Description</label>
            <textarea
              id="input-case-description"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 resize-none"
              placeholder="Optional description"
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div className="flex gap-3">
            <button
              id="btn-submit-case"
              type="submit"
              disabled={creating}
              className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium px-4 py-2 rounded-lg transition"
            >
              {creating ? "Creating…" : "Create Case"}
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="text-gray-400 hover:text-gray-200 text-sm px-4 py-2 transition"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {error && (
        <div id="error-cases" className="mb-4 p-3 bg-red-950 border border-red-800 rounded-lg text-red-300 text-sm">
          Error: {error}
        </div>
      )}

      {loading ? (
        <div className="text-gray-500 text-sm">Loading cases…</div>
      ) : cases.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <p className="text-lg mb-2">No cases yet</p>
          <p className="text-sm">Click &quot;+ New Case&quot; to create your first investigation case.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {cases.map((c) => (
            <Link
              key={c.id}
              href={`/cases/${c.id}`}
              id={`case-${c.id}`}
              className="block bg-gray-900 border border-gray-800 hover:border-indigo-600 rounded-xl p-5 transition group"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <h2 className="text-base font-semibold text-gray-100 group-hover:text-indigo-300 truncate">
                    {c.title}
                  </h2>
                  {c.description && (
                    <p className="text-sm text-gray-500 mt-1 truncate">{c.description}</p>
                  )}
                  <p className="text-xs text-gray-600 mt-2">
                    {c.created_by && <span className="mr-3">by {c.created_by}</span>}
                    {new Date(c.created_at).toLocaleString()}
                  </p>
                </div>
                <span
                  className={`shrink-0 text-xs font-medium px-2 py-1 rounded border ${
                    c.status === "OPEN"
                      ? "bg-green-900 text-green-300 border-green-700"
                      : "bg-gray-800 text-gray-400 border-gray-700"
                  }`}
                >
                  {c.status}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
