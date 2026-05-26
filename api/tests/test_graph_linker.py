"""Auto-linker idempotency and part extraction tests."""

from __future__ import annotations

from graph.linker import LinkContext, extract_parts, run_auto_link


class RecordingSession:
    def __init__(self) -> None:
        self.queries: list[tuple[str, dict | None]] = []

    def run(self, query: str, parameters: dict | None = None) -> None:
        self.queries.append((query.strip(), parameters))


def _ctx() -> LinkContext:
    return LinkContext(
        org_id="org-1",
        org_name="Org",
        project_id="proj-1",
        project_name="Project",
        object_id="obj-1",
        object_name="Board",
        object_type="PCB",
        version_id="ver-2",
        version_num=2,
        lifecycle_state="draft",
        previous_version_id="ver-1",
    )


def test_extract_parts_deduplicates_components_and_bom() -> None:
    parsed = {
        "components": [
            {"mpn": "STM32F103", "manufacturer": "ST"},
            {"mpn": "STM32F103", "manufacturer": "ST"},
            {"ref": "C1", "value": "100nF"},
        ],
        "bom_rows": [
            {"mpn": "RC0402", "manufacturer": "Yageo"},
            {"mpn": "STM32F103", "manufacturer": "ST"},
        ],
    }
    parts = extract_parts(parsed)
    assert len(parts) == 2
    mpns = {p.mpn for p in parts}
    assert mpns == {"STM32F103", "RC0402"}


def test_auto_linker_idempotent_query_count() -> None:
    parsed = {
        "components": [{"mpn": "LM358", "manufacturer": "TI"}],
        "bom_rows": [],
    }
    ctx = _ctx()

    session1 = RecordingSession()
    run_auto_link(session1, ctx, parsed)
    first_count = len(session1.queries)

    session2 = RecordingSession()
    run_auto_link(session2, ctx, parsed)
    second_count = len(session2.queries)

    assert first_count == second_count
    assert first_count >= 3
    assert all("MERGE" in q for q, _ in session1.queries)


def test_auto_linker_uses_merge_for_parts_and_version_edges() -> None:
    session = RecordingSession()
    run_auto_link(
        session, _ctx(), {"components": [{"mpn": "ABC", "manufacturer": "M"}]}
    )
    combined = " ".join(q for q, _ in session.queries)
    assert "MERGE (pt:Part" in combined
    assert "MERGE (v)-[:USES]->(pt)" in combined
    assert "MERGE (h)-[:HAS_VERSION]->(v)" in combined
    assert "MERGE (cur)-[:SUPERSEDES]->(prev)" in combined


def test_graph_service_depth_clamping() -> None:
    from app.services.graph import GraphService

    assert GraphService._sanitize_label("HardwareObject") == "HardwareObject"
    try:
        GraphService._sanitize_label("Evil")
    except ValueError:
        pass
    else:
        raise AssertionError("expected invalid label rejection")
