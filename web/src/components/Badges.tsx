import { parseBadgeClass, stateBadgeClass } from "../lib/lifecycle";

export function LifecycleBadge({ state }: { state: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${stateBadgeClass(state)}`}
    >
      {state.replace("_", " ")}
    </span>
  );
}

export function ParseBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${parseBadgeClass(status)}`}
    >
      {status}
    </span>
  );
}

export function TypeIcon({ type }: { type: string }) {
  const icons: Record<string, string> = {
    PCB: "⬡",
    BOM: "☰",
    GERBER: "▣",
    STEP: "◫",
    FIRMWARE: "⚡",
  };
  return (
    <span className="text-lg" title={type} aria-hidden>
      {icons[type] ?? "📄"}
    </span>
  );
}
