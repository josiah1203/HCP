import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { LifecycleBadge, ParseBadge, TypeIcon } from "../components/Badges";
import { UploadZone } from "../components/UploadZone";
import type { TreeNode } from "../api/types";

function TreeItem({ node, depth = 0 }: { node: TreeNode; depth?: number }) {
  const [open, setOpen] = useState(depth < 2);
  const hasChildren = (node.children?.length ?? 0) > 0;

  return (
    <li className="list-none">
      <div
        className="flex items-center gap-2 py-1.5 hover:bg-slate-50 rounded px-1"
        style={{ paddingLeft: `${depth * 16}px` }}
      >
        {hasChildren ? (
          <button
            type="button"
            aria-expanded={open}
            onClick={() => setOpen(!open)}
            className="w-5 text-slate-500"
          >
            {open ? "▼" : "▶"}
          </button>
        ) : (
          <span className="w-5" />
        )}
        <TypeIcon type={node.object_type} />
        <Link to={`/objects/${node.id}`} className="font-medium text-hcp-600 hover:underline">
          {node.name}
        </Link>
        {node.lifecycle_state && <LifecycleBadge state={node.lifecycle_state} />}
        {node.parse_status && <ParseBadge status={node.parse_status} />}
        {node.version_num !== undefined && (
          <span className="text-xs text-slate-500">v{node.version_num}</span>
        )}
      </div>
      {open && hasChildren && (
        <ul>
          {node.children?.map((child) => (
            <TreeItem key={child.id} node={child} depth={depth + 1} />
          ))}
        </ul>
      )}
    </li>
  );
}

function flattenForCsv(nodes: TreeNode[]): string[][] {
  const rows: string[][] = [["id", "name", "type", "state", "version"]];
  function walk(n: TreeNode) {
    rows.push([
      n.id,
      n.name,
      n.object_type,
      n.lifecycle_state ?? "",
      String(n.version_num ?? ""),
    ]);
    n.children?.forEach(walk);
  }
  nodes.forEach(walk);
  return rows;
}

export function ProjectTreePage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { client } = useAuth();
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState("");

  const projectQuery = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => client.getProject(projectId!),
    enabled: Boolean(projectId),
  });

  const treeQuery = useQuery({
    queryKey: ["project-tree", projectId],
    queryFn: () => client.getProjectTree(projectId!),
    enabled: Boolean(projectId),
    retry: false,
  });

  const tree = useMemo(() => {
    const data = treeQuery.data?.data ?? [];
    if (!filter.trim()) return data;
    const q = filter.toLowerCase();
    function match(n: TreeNode): TreeNode | null {
      const kids = (n.children ?? [])
        .map(match)
        .filter((c): c is TreeNode => c !== null);
      if (n.name.toLowerCase().includes(q) || kids.length > 0) {
        return { ...n, children: kids.length ? kids : n.children };
      }
      return null;
    }
    return data.map(match).filter((n): n is TreeNode => n !== null);
  }, [treeQuery.data, filter]);

  const uploadMutation = useMutation({
    mutationFn: (files: FileList) => {
      const tasks = Array.from(files).map((file) =>
        client.uploadObject(file, projectId!, file.name.replace(/\.[^.]+$/, ""))
      );
      return Promise.all(tasks);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["project-tree", projectId] });
    },
  });

  function exportCsv() {
    const rows = flattenForCsv(tree);
    const csv = rows.map((r) => r.map((c) => `"${c.replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `project-${projectId}-tree.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link to="/" className="text-sm text-hcp-600 hover:underline">
            ← Dashboard
          </Link>
          <h1 className="text-2xl font-bold mt-1">
            {projectQuery.data?.name ?? "Project"}
          </h1>
        </div>
        <button
          type="button"
          onClick={exportCsv}
          disabled={tree.length === 0}
          className="rounded border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50 disabled:opacity-50"
        >
          Export CSV
        </button>
      </header>

      <input
        type="search"
        placeholder="Filter objects…"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="w-full max-w-md rounded border border-slate-300 px-3 py-2 text-sm"
        aria-label="Filter project tree"
      />

      <UploadZone
        label="Upload to this project"
        disabled={uploadMutation.isPending}
        onFiles={(f) => uploadMutation.mutate(f)}
      />

      {treeQuery.isError && (
        <p className="text-sm text-amber-800 bg-amber-50 rounded p-3">
          Project tree API not available yet. Upload files from the dashboard; they appear here
          when <code className="text-xs">GET /v1/projects/:id/tree</code> is implemented.
        </p>
      )}

      {tree.length === 0 && !treeQuery.isError ? (
        <p className="text-sm text-slate-500">No objects in this project.</p>
      ) : (
        <ul className="bg-white rounded-lg border border-slate-200 p-3">
          {tree.map((node) => (
            <TreeItem key={node.id} node={node} />
          ))}
        </ul>
      )}
    </div>
  );
}
