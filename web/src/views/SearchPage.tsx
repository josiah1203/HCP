import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { LifecycleBadge, TypeIcon } from "../components/Badges";

export function SearchPage() {
  const { client } = useAuth();
  const [q, setQ] = useState("");
  const [type, setType] = useState("");
  const [state, setState] = useState("");
  const [projectId, setProjectId] = useState("");
  const [submitted, setSubmitted] = useState("");

  const params = useMemo(() => {
    const p = new URLSearchParams();
    if (submitted) p.set("q", submitted);
    if (type) p.set("type", type);
    if (state) p.set("state", state);
    if (projectId) p.set("project_id", projectId);
    p.set("page", "1");
    p.set("per_page", "20");
    return p;
  }, [submitted, type, state, projectId]);

  const searchQuery = useQuery({
    queryKey: ["search", params.toString()],
    queryFn: () => client.search(params),
    enabled: submitted.length > 0,
    retry: false,
  });

  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: () => client.listProjects(),
  });

  const facets = searchQuery.data?.facets;

  return (
    <div className="flex flex-col lg:flex-row gap-6">
      <aside className="lg:w-64 shrink-0 space-y-4" aria-label="Search facets">
        <h2 className="font-semibold text-slate-800">Filters</h2>
        <label className="block text-sm">
          Type
          <select
            value={type}
            onChange={(e) => setType(e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
          >
            <option value="">Any</option>
            {(facets?.types ?? []).map((t) => (
              <option key={t.value} value={t.value}>
                {t.value} ({t.count})
              </option>
            ))}
            {!facets?.types?.length && (
              <>
                <option value="PCB">PCB</option>
                <option value="BOM">BOM</option>
                <option value="GERBER">GERBER</option>
                <option value="STEP">STEP</option>
              </>
            )}
          </select>
        </label>
        <label className="block text-sm">
          State
          <select
            value={state}
            onChange={(e) => setState(e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
          >
            <option value="">Any</option>
            {(facets?.states ?? []).map((s) => (
              <option key={s.value} value={s.value}>
                {s.value} ({s.count})
              </option>
            ))}
            {!facets?.states?.length && (
              <>
                <option value="draft">draft</option>
                <option value="released">released</option>
              </>
            )}
          </select>
        </label>
        <label className="block text-sm">
          Project
          <select
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
          >
            <option value="">Any</option>
            {(projectsQuery.data?.data ?? []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
      </aside>

      <div className="flex-1 space-y-4">
        <h1 className="text-2xl font-bold text-hcp-900">Search</h1>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            setSubmitted(q.trim());
          }}
        >
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search hardware objects…"
            className="flex-1 rounded-lg border border-slate-300 px-4 py-2"
            aria-label="Search query"
          />
          <button
            type="submit"
            className="rounded-lg bg-hcp-600 text-white px-4 py-2 font-medium hover:bg-hcp-700"
          >
            Search
          </button>
        </form>

        {searchQuery.isError && (
          <p className="text-sm text-amber-800 bg-amber-50 rounded p-3">
            Search API not available yet. Implement <code className="text-xs">GET /v1/search</code>{" "}
            on the API to enable full-text search.
          </p>
        )}

        {searchQuery.isLoading && submitted && (
          <p className="text-sm text-slate-500">Searching…</p>
        )}

        <ul className="space-y-3">
          {(searchQuery.data?.data ?? []).map((hit) => (
            <li
              key={hit.id}
              className="rounded-lg border border-slate-200 bg-white p-4 hover:border-hcp-400"
            >
              <div className="flex items-center gap-2">
                {hit.object_type && <TypeIcon type={hit.object_type} />}
                <Link
                  to={`/objects/${hit.id}`}
                  className="font-medium text-hcp-600 hover:underline"
                >
                  {hit.name}
                </Link>
                {hit.lifecycle_state && <LifecycleBadge state={hit.lifecycle_state} />}
              </div>
              {hit.snippet && (
                <p
                  className="text-sm text-slate-600 mt-2"
                  dangerouslySetInnerHTML={{ __html: hit.snippet }}
                />
              )}
            </li>
          ))}
        </ul>

        {submitted && !searchQuery.isLoading && (searchQuery.data?.data ?? []).length === 0 && !searchQuery.isError && (
          <p className="text-sm text-slate-500">No results.</p>
        )}
      </div>
    </div>
  );
}
