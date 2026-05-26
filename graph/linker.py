from __future__ import annotations
"""Idempotent auto-linker — merges graph state from ParsedOutput (HCP §10.3)."""

from dataclasses import dataclass
from typing import Any, Protocol


class GraphSession(Protocol):
    def run(self, query: str, parameters: dict[str, Any] | None = None) -> Any: ...


@dataclass(frozen=True)
class PartRef:
    mpn: str
    manufacturer: str
    lifecycle: str | None = None


@dataclass(frozen=True)
class LinkContext:
    org_id: str
    org_name: str
    project_id: str
    project_name: str
    object_id: str
    object_name: str
    object_type: str
    version_id: str
    version_num: int
    lifecycle_state: str
    previous_version_id: str | None


MANUAL_REL_TYPES = frozenset(
    {"TARGETS", "VALIDATES", "CONTAINS", "SATISFIES", "SOURCED_FROM"}
)
AUTO_REL_TYPES = frozenset({"USES", "HAS_VERSION", "SUPERSEDES"})
# V2 (ADR-003): DERIVED_FROM / REPRESENTS — merged in graph.tasks.auto_link_version for
# derived uploads today; bundle-manifest + converter path will call linker helpers here.
DERIVED_REL_TYPES = frozenset({"DERIVED_FROM", "REPRESENTS"})


def extract_parts(parsed: dict[str, Any]) -> list[PartRef]:
    """Collect unique parts from components and BOM rows."""
    seen: set[tuple[str, str]] = set()
    parts: list[PartRef] = []

    for comp in parsed.get("components") or []:
        mpn = (comp.get("mpn") or "").strip()
        mfr = (comp.get("manufacturer") or "Unknown").strip() or "Unknown"
        if not mpn:
            continue
        key = (mpn, mfr)
        if key not in seen:
            seen.add(key)
            parts.append(PartRef(mpn=mpn, manufacturer=mfr))

    for row in parsed.get("bom_rows") or []:
        mpn = (row.get("mpn") or "").strip()
        mfr = (row.get("manufacturer") or "Unknown").strip() or "Unknown"
        if not mpn:
            continue
        key = (mpn, mfr)
        if key not in seen:
            seen.add(key)
            parts.append(PartRef(mpn=mpn, manufacturer=mfr))

    return parts


def run_auto_link(session: GraphSession, ctx: LinkContext, parsed: dict[str, Any]) -> int:
    """
    Idempotent graph merge for one parsed version. Returns count of USES edges ensured.
    """
    _ensure_scaffold(session, ctx)
    parts = extract_parts(parsed)
    uses_count = _link_parts(session, ctx, parts)
    _link_version_edges(session, ctx)
    return uses_count


def _ensure_scaffold(session: GraphSession, ctx: LinkContext) -> None:
    session.run(
        """
        MERGE (o:Org {org_id: $org_id})
        ON CREATE SET o.name = $org_name
        MERGE (p:Project {project_id: $project_id})
        ON CREATE SET p.org_id = $org_id, p.name = $project_name
        MERGE (h:HardwareObject {object_id: $object_id})
        ON CREATE SET h.org_id = $org_id, h.name = $object_name, h.type = $object_type
        ON MATCH SET h.name = $object_name, h.type = $object_type
        MERGE (v:Version {version_id: $version_id})
        ON CREATE SET
            v.org_id = $org_id,
            v.object_id = $object_id,
            v.version_num = $version_num,
            v.state = $lifecycle_state
        ON MATCH SET
            v.version_num = $version_num,
            v.state = $lifecycle_state
        MERGE (p)-[:CONTAINS]->(h)
        """,
        {
            "org_id": ctx.org_id,
            "org_name": ctx.org_name,
            "project_id": ctx.project_id,
            "project_name": ctx.project_name,
            "object_id": ctx.object_id,
            "object_name": ctx.object_name,
            "object_type": ctx.object_type,
            "version_id": ctx.version_id,
            "version_num": ctx.version_num,
            "lifecycle_state": ctx.lifecycle_state,
        },
    )


def _link_parts(session: GraphSession, ctx: LinkContext, parts: list[PartRef]) -> int:
    count = 0
    for part in parts:
        session.run(
            """
            MATCH (v:Version {version_id: $version_id})
            WHERE v.org_id = $org_id
            MERGE (pt:Part {mpn: $mpn, manufacturer: $manufacturer})
            ON CREATE SET pt.lifecycle = $lifecycle
            MERGE (v)-[:USES]->(pt)
            """,
            {
                "org_id": ctx.org_id,
                "version_id": ctx.version_id,
                "mpn": part.mpn,
                "manufacturer": part.manufacturer,
                "lifecycle": part.lifecycle,
            },
        )
        count += 1
    return count


def _link_version_edges(session: GraphSession, ctx: LinkContext) -> None:
    session.run(
        """
        MATCH (h:HardwareObject {object_id: $object_id}), (v:Version {version_id: $version_id})
        WHERE h.org_id = $org_id AND v.org_id = $org_id
        MERGE (h)-[:HAS_VERSION]->(v)
        """,
        {
            "org_id": ctx.org_id,
            "object_id": ctx.object_id,
            "version_id": ctx.version_id,
        },
    )
    if ctx.previous_version_id:
        session.run(
            """
            MATCH (cur:Version {version_id: $version_id}), (prev:Version {version_id: $prev_id})
            WHERE cur.org_id = $org_id AND prev.org_id = $org_id
            MERGE (cur)-[:SUPERSEDES]->(prev)
            """,
            {
                "org_id": ctx.org_id,
                "version_id": ctx.version_id,
                "prev_id": ctx.previous_version_id,
            },
        )
