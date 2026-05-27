"""Graph Celery task integration — parse_complete → auto-link → event stream."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from graph.linker import LinkContext, extract_parts, run_auto_link


class RecordingSession:
    def __init__(self) -> None:
        self.queries: list[tuple[str, dict | None]] = []

    def run(self, query: str, parameters: dict | None = None) -> None:
        self.queries.append((query.strip(), parameters))

    def __enter__(self) -> RecordingSession:
        return self

    def __exit__(self, *args: object) -> None:
        pass


def test_auto_link_version_publishes_graph_event() -> None:
    version_id = str(uuid.uuid4())
    org_id = uuid.uuid4()
    project_id = uuid.uuid4()
    object_id = uuid.uuid4()

    version = MagicMock()
    version.id = uuid.UUID(version_id)
    version.org_id = org_id
    version.object_id = object_id
    version.version_num = 1
    version.parse_status = "complete"
    version.parsed_key = "parsed/key.json"
    version.lifecycle_state = "draft"
    version.domain = None
    version.source_tool = None
    version.representation = None
    version.derived_from_version_id = None
    version.filename = "board.kicad_pcb"
    version.parsed_at = datetime.now(timezone.utc)

    hw = MagicMock()
    hw.id = object_id
    hw.project_id = project_id
    hw.name = "Board"
    hw.object_type = "PCB"
    hw.domain = None
    hw.source_tool = None
    hw.representation = None

    project = MagicMock()
    project.id = project_id
    project.name = "Proj"

    org = MagicMock()
    org.name = "Org"

    parsed = {"components": [{"mpn": "LM358", "manufacturer": "TI"}], "bom_rows": []}

    mock_db = MagicMock()
    mock_db.get.side_effect = lambda model, pk: {
        version.id: version,
        object_id: hw,
        project_id: project,
        org_id: org,
    }.get(pk)
    mock_db.scalar.return_value = None

    mock_graph = MagicMock()
    mock_graph.session.return_value = RecordingSession()

    mock_search = MagicMock()

    with (
        patch("sqlalchemy.create_engine"),
        patch("sqlalchemy.orm.sessionmaker", return_value=lambda: mock_db),
        patch("app.services.graph.get_graph_service", return_value=mock_graph),
        patch("app.services.search.get_search_service", return_value=mock_search),
        patch("infra.pal.factory.get_storage_provider") as mock_storage,
        patch("graph.tasks.enrich_parts_for_version") as mock_enrich,
        patch("app.services.events.EventPublisher") as mock_pub_cls,
    ):
        mock_storage.return_value.download.return_value = json.dumps(parsed).encode()
        mock_pub = mock_pub_cls.return_value
        mock_enrich.delay = MagicMock()

        from graph.tasks import auto_link_version

        result = auto_link_version(version_id)

    assert result["status"] == "ok"
    assert result["uses_edges"] == 1
    mock_search.index_version.assert_called_once()
    mock_pub.publish.assert_called_once()
    call = mock_pub.publish.call_args.kwargs
    assert call["event_type"] == "graph_auto_link_complete"
    assert call["dedupe_key"] == f"version:{version_id}:auto_link_complete"
    assert call["project_id"] == project_id


def test_extract_parts_used_by_indexing() -> None:
    parsed = {
        "components": [{"mpn": "A", "manufacturer": "M"}],
        "bom_rows": [{"mpn": "B", "manufacturer": "M"}],
    }
    parts = extract_parts(parsed)
    assert {p.mpn for p in parts} == {"A", "B"}


def test_run_auto_link_returns_uses_count() -> None:
    session = RecordingSession()
    ctx = LinkContext(
        org_id="o",
        org_name="O",
        project_id="p",
        project_name="P",
        object_id="obj",
        object_name="Obj",
        object_type="PCB",
        version_id="v",
        version_num=1,
        lifecycle_state="draft",
        previous_version_id=None,
    )
    count = run_auto_link(
        session, ctx, {"components": [{"mpn": "X", "manufacturer": "Y"}]}
    )
    assert count == 1
