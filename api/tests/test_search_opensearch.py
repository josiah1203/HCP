"""OpenSearch search service — org filter and facets."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from app.services.search import OpenSearchIndex, SearchParams


def test_opensearch_search_applies_org_term_and_facets() -> None:
    org_id = uuid.uuid4()
    client = MagicMock()
    client.indices.exists.return_value = True
    client.search.return_value = {
        "hits": {
            "total": {"value": 1},
            "hits": [
                {
                    "_source": {
                        "object_id": "obj-1",
                        "name": "Board",
                        "object_type": "PCB",
                        "project_id": "p-1",
                        "version_num": 1,
                        "lifecycle_state": "draft",
                        "version_id": "v-1",
                    }
                }
            ],
        },
        "aggregations": {
            "types": {"buckets": [{"key": "PCB", "doc_count": 1}]},
            "domains": {"buckets": []},
            "source_tools": {"buckets": []},
            "representations": {"buckets": []},
            "states": {"buckets": [{"key": "draft", "doc_count": 1}]},
            "projects": {"buckets": [{"key": "p-1", "doc_count": 1}]},
        },
    }

    with patch("app.services.search.OpenSearch", return_value=client):
        idx = OpenSearchIndex("http://localhost:9200", "hcp-versions-test")
        result = idx.search(SearchParams(org_id=org_id, q="board"))

    body = client.search.call_args.kwargs.get("body") or client.search.call_args[0][1]
    must = body["query"]["bool"]["must"]
    assert {"term": {"org_id": str(org_id)}} in must
    assert "aggs" in body
    assert result["facets"]["types"]["PCB"] == 1
    assert len(result["data"]) == 1
