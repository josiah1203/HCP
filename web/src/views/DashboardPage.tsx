import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { UploadZone } from "../components/UploadZone";
import { loadRecentUploads, pushRecentUpload, type RecentUpload } from "../lib/recentUploads";

export function DashboardPage() {
  const { client } = useAuth();
  const queryClient = useQueryClient();
  const [recent, setRecent] = useState<RecentUpload[]>(loadRecentUploads);
  const [projectId, setProjectId] = useState("");
  const [uploadError, setUploadError] = useState<string | null>(null);

  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: () => client.listProjects(),
  });

  const projects = projectsQuery.data?.data ?? [];

  const uploadMutation = useMutation({
    mutationFn: async (files: FileList) => {
      const pid = projectId || projects[0]?.id;
      if (!pid) throw new Error("Create a project first");
      const results = [];
      for (const file of Array.from(files)) {
        const name = file.name.replace(/\.[^.]+$/, "");
        results.push(await client.uploadObject(file, pid, name));
      }
      return results;
    },
    onSuccess: (results) => {
      let updated = recent;
      for (const r of results) {
        updated = pushRecentUpload(r);
      }
      setRecent(updated);
      setUploadError(null);
      void queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: (err: Error) => setUploadError(err.message),
  });

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-bold text-hcp-900">Dashboard</h1>
        <p className="text-slate-600 text-sm mt-1">
          Recent uploads, projects, and quick upload
        </p>
      </header>

      <section aria-labelledby="upload-heading">
        <h2 id="upload-heading" className="text-lg font-semibold mb-3">
          Upload
        </h2>
        <div className="mb-3 flex flex-wrap gap-3 items-center">
          <label className="text-sm font-medium">
            Project
            <select
              value={projectId || projects[0]?.id || ""}
              onChange={(e) => setProjectId(e.target.value)}
              className="ml-2 rounded border border-slate-300 px-2 py-1 text-sm"
            >
              {projects.length === 0 && <option value="">No projects</option>}
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="text-sm text-hcp-600 hover:underline"
            onClick={() => {
              const name = window.prompt("Project name");
              if (!name) return;
              void client.createProject(name).then(() => {
                void queryClient.invalidateQueries({ queryKey: ["projects"] });
              });
            }}
          >
            + New project
          </button>
        </div>
        {uploadError && (
          <p className="text-sm text-red-600 mb-2" role="alert">
            {uploadError}
          </p>
        )}
        <UploadZone
          disabled={uploadMutation.isPending}
          onFiles={(files) => uploadMutation.mutate(files)}
        />
      </section>

      <section aria-labelledby="recent-heading">
        <h2 id="recent-heading" className="text-lg font-semibold mb-3">
          Recent uploads
        </h2>
        {recent.length === 0 ? (
          <p className="text-sm text-slate-500">No uploads this session yet.</p>
        ) : (
          <ul className="divide-y divide-slate-200 bg-white rounded-lg border border-slate-200">
            {recent.map((u) => (
              <li key={u.objectId} className="px-4 py-3 flex justify-between items-center">
                <div>
                  <Link
                    to={`/objects/${u.objectId}`}
                    className="font-medium text-hcp-600 hover:underline"
                  >
                    {u.objectName}
                  </Link>
                  <p className="text-xs text-slate-500">
                    {u.filename} · v{u.versionNum} · {u.objectType}
                  </p>
                </div>
                <Link
                  to={`/projects/${u.projectId}`}
                  className="text-xs text-slate-600 hover:text-hcp-600"
                >
                  Project
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="projects-heading">
        <h2 id="projects-heading" className="text-lg font-semibold mb-3">
          Projects
        </h2>
        {projectsQuery.isLoading && <p className="text-sm text-slate-500">Loading…</p>}
        {projectsQuery.isError && (
          <p className="text-sm text-red-600">Failed to load projects</p>
        )}
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => (
            <li key={p.id}>
              <Link
                to={`/projects/${p.id}`}
                className="block rounded-lg border border-slate-200 bg-white p-4 hover:border-hcp-500 hover:shadow-sm"
              >
                <span className="font-medium">{p.name}</span>
                {p.description && (
                  <p className="text-xs text-slate-500 mt-1 line-clamp-2">{p.description}</p>
                )}
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
