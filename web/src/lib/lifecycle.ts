const TRANSITIONS: Record<string, string[]> = {
  draft: ["in_review"],
  in_review: ["released", "draft"],
  released: ["obsolete"],
  obsolete: [],
};

export function allowedTransitions(
  current: string,
  role: string
): string[] {
  const next = TRANSITIONS[current] ?? [];
  if (role === "admin" || role === "approver") return next;
  if (role === "editor") {
    return next.filter((s) => s === "in_review" || s === "draft");
  }
  return [];
}

export function stateBadgeClass(state: string): string {
  const map: Record<string, string> = {
    draft: "bg-slate-200 text-slate-800",
    in_review: "bg-amber-100 text-amber-900",
    released: "bg-emerald-100 text-emerald-900",
    obsolete: "bg-rose-100 text-rose-900",
  };
  return map[state] ?? "bg-slate-100 text-slate-700";
}

export function parseBadgeClass(status: string): string {
  const map: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800",
    complete: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
  };
  return map[status] ?? "bg-slate-100 text-slate-600";
}
