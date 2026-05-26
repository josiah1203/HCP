import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { lazy, Suspense, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { LifecycleBadge, ParseBadge, TypeIcon } from "../components/Badges";
import { allowedTransitions } from "../lib/lifecycle";

const GraphView = lazy(() =>
  import("../components/GraphView").then((m) => ({ default: m.GraphView }))
);

type Tab = "preview" | "parsed" | "graph" | "audit";

export function ObjectDetailPage() {
  const { objectId } = useParams<{ objectId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const versionParam = searchParams.get("v");
  const tab = (searchParams.get("tab") as Tab) || "parsed";
  const { client, user } = useAuth();
  const queryClient = useQueryClient();
  const [promoteError, setPromoteError] = useState<string | null>(null);

  const objectQuery = useQuery({
    queryKey: ["object", objectId],
    queryFn: () => client.getObject(objectId!),
    enabled: Boolean(objectId),
  });

  const versionsQuery = useQuery({
    queryKey: ["versions", objectId],
    queryFn: () => client.listVersions(objectId!),
    enabled: Boolean(objectId),
  });

  const versions = versionsQuery.data?.data ?? [];
  const selectedVersion =
    versions.find((v) => String(v.version_num) === versionParam) ??
    versions[0] ??
    objectQuery.data?.latest_version;

  const bomQuery = useQuery({
    queryKey: ["bom", objectId, selectedVersion?.version_num],
    queryFn: () => client.getBom(objectId!, selectedVersion?.version_num),
    enabled: Boolean(objectId && selectedVersion && tab === "parsed"),
    retry: false,
  });

  const parsedQuery = useQuery({
    queryKey: ["parsed", objectId, selectedVersion?.version_num],
    queryFn: () => client.getParsed(objectId!, selectedVersion!.version_num),
    enabled: Boolean(objectId && selectedVersion && tab === "parsed" && bomQuery.isError),
    retry: false,
  });

  const graphQuery = useQuery({
    queryKey: ["graph", objectId],
    queryFn: () => client.getGraph(objectId!, 2),
    enabled: Boolean(objectId && tab === "graph"),
    retry: false,
  });

  const auditQuery = useQuery({
    queryKey: ["audit", objectId],
    queryFn: () => client.getAuditLog(objectId!),
    enabled: Boolean(objectId && tab === "audit"),
    retry: false,
  });

  const promoteMutation = useMutation({
    mutationFn: (targetState: string) =>
      client.promote(objectId!, selectedVersion!.version_num, targetState),
    onSuccess: () => {
      setPromoteError(null);
      void queryClient.invalidateQueries({ queryKey: ["object", objectId] });
      void queryClient.invalidateQueries({ queryKey: ["versions", objectId] });
    },
    onError: (err: Error) => setPromoteError(err.message),
  });

  const obj = objectQuery.data;
  const transitions = selectedVersion
    ? allowedTransitions(selectedVersion.lifecycle_state, user?.role ?? "viewer")
    : [];

  function setTab(next: Tab) {
    const p = new URLSearchParams(searchParams);
    p.set("tab", next);
    setSearchParams(p);
  }

  const bomLines = bomQuery.data?.lines ?? [];
  const components =
    (parsedQuery.data?.pcb as { components?: Array<Record<string, unknown>> } | undefined)
      ?.components ?? parsedQuery.data?.components;

  return (
    <div className="space-y-6">
      <header>
        <Link
          to={obj ? `/projects/${obj.project_id}` : "/"}
          className="text-sm text-hcp-600 hover:underline"
        >
          ← Project
        </Link>
        {obj && (
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <TypeIcon type={obj.object_type} />
            <h1 className="text-2xl font-bold">{obj.name}</h1>
            <span className="text-sm text-slate-500">{obj.object_type}</span>
            {selectedVersion && (
              <>
                <LifecycleBadge state={selectedVersion.lifecycle_state} />
                <ParseBadge status={selectedVersion.parse_status} />
                <span className="text-sm">v{selectedVersion.version_num}</span>
              </>
            )}
          </div>
        )}
      </header>

      {versions.length > 0 && (
        <section aria-label="Version history">
          <h2 className="text-sm font-semibold text-slate-700 mb-2">Version timeline</h2>
          <ol className="flex gap-2 overflow-x-auto pb-2">
            {versions.map((v) => (
              <li key={v.id}>
                <button
                  type="button"
                  onClick={() => {
                    const p = new URLSearchParams(searchParams);
                    p.set("v", String(v.version_num));
                    setSearchParams(p);
                  }}
                  className={`rounded-lg border px-3 py-2 text-left text-sm min-w-[100px] ${
                    selectedVersion?.version_num === v.version_num
                      ? "border-hcp-500 bg-hcp-50"
                      : "border-slate-200 bg-white"
                  }`}
                >
                  <div className="font-medium">v{v.version_num}</div>
                  <div className="text-xs text-slate-500">{v.filename}</div>
                </button>
              </li>
            ))}
          </ol>
        </section>
      )}

      {selectedVersion && transitions.length > 0 && (
        <section aria-label="Lifecycle actions" className="flex flex-wrap gap-2 items-center">
          <span className="text-sm font-medium text-slate-600">Transition:</span>
          {transitions.map((state) => (
            <button
              key={state}
              type="button"
              disabled={promoteMutation.isPending}
              onClick={() => promoteMutation.mutate(state)}
              className="rounded bg-hcp-600 text-white text-sm px-3 py-1 hover:bg-hcp-700 disabled:opacity-50"
            >
              → {state.replace("_", " ")}
            </button>
          ))}
          {promoteError && (
            <span className="text-sm text-red-600" role="alert">
              {promoteError}
            </span>
          )}
        </section>
      )}

      <nav className="flex gap-1 border-b border-slate-200" aria-label="Object tabs">
        {(["preview", "parsed", "graph", "audit"] as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize ${
              tab === t
                ? "border-b-2 border-hcp-600 text-hcp-700"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            {t === "parsed" ? "Parsed / BOM" : t}
          </button>
        ))}
      </nav>

      {tab === "preview" && (
        <div className="grid sm:grid-cols-2 gap-4">
          <div className="rounded-lg border border-slate-200 bg-white p-6 text-center text-slate-500">
            <p className="font-medium text-slate-700 mb-2">STEP preview</p>
            <p className="text-sm">Three.js viewer stub — wire when STEP parse is available.</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-6 text-center text-slate-500">
            <p className="font-medium text-slate-700 mb-2">Gerber preview</p>
            <p className="text-sm">js-gerber-viewer stub — wire when Gerber layers are indexed.</p>
          </div>
        </div>
      )}

      {tab === "parsed" && (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          {bomLines.length > 0 ? (
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  {["ref", "mpn", "manufacturer", "quantity", "value"].map((col) => (
                    <th key={col} className="px-3 py-2 text-left font-medium capitalize">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {bomLines.map((line, i) => (
                  <tr key={i} className="border-t border-slate-100">
                    <td className="px-3 py-2">{line.ref ?? "—"}</td>
                    <td className="px-3 py-2">{line.mpn ?? "—"}</td>
                    <td className="px-3 py-2">{line.manufacturer ?? "—"}</td>
                    <td className="px-3 py-2">{line.quantity ?? "—"}</td>
                    <td className="px-3 py-2">{line.value ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : Array.isArray(components) && components.length > 0 ? (
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-3 py-2 text-left">Ref</th>
                  <th className="px-3 py-2 text-left">Value</th>
                  <th className="px-3 py-2 text-left">Footprint</th>
                </tr>
              </thead>
              <tbody>
                {components.map((c, i) => (
                  <tr key={i} className="border-t border-slate-100">
                    <td className="px-3 py-2">{String(c.ref ?? "—")}</td>
                    <td className="px-3 py-2">{String(c.value ?? "—")}</td>
                    <td className="px-3 py-2">{String(c.footprint ?? "—")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="p-6 text-sm text-slate-500">
              No parsed BOM or component data yet. Available when parse completes and BOM/parsed
              endpoints respond.
            </p>
          )}
        </div>
      )}

      {tab === "graph" && (
        <Suspense fallback={<p className="text-sm text-slate-500">Loading graph…</p>}>
          <GraphView
            nodes={graphQuery.data?.nodes ?? []}
            edges={graphQuery.data?.edges ?? []}
            centerId={objectId!}
          />
        </Suspense>
      )}

      {tab === "audit" && (
        <div className="rounded-lg border border-slate-200 bg-white divide-y">
          {(auditQuery.data?.data ?? []).length === 0 ? (
            <p className="p-6 text-sm text-slate-500">
              No audit entries yet. Logged on version creation and state transitions.
            </p>
          ) : (
            auditQuery.data?.data.map((entry) => (
              <div key={entry.id} className="px-4 py-3 text-sm">
                <div className="font-medium">{entry.event_type}</div>
                <div className="text-slate-600">
                  {entry.actor_email} · {new Date(entry.created_at).toLocaleString()}
                </div>
                {(entry.from_state || entry.to_state) && (
                  <div className="text-xs text-slate-500">
                    {entry.from_state} → {entry.to_state}
                  </div>
                )}
                {entry.comment && <p className="text-xs mt-1">{entry.comment}</p>}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
