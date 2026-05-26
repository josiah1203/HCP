from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from app.services.bom import BOMService


def test_bom_diff_reports_added_removed_and_changed() -> None:
    object_id = uuid.uuid4()
    org_id = uuid.uuid4()
    service = BOMService(MagicMock())
    service.get_bom = MagicMock(
        side_effect=[
            {
                "object_id": str(object_id),
                "version_num": 1,
                "rows": [
                    {"mpn": "R1", "manufacturer": "Acme", "qty": 1},
                    {"mpn": "R2", "manufacturer": "Acme", "qty": 5},
                ],
                "components": [],
            },
            {
                "object_id": str(object_id),
                "version_num": 2,
                "rows": [
                    {"mpn": "R1", "manufacturer": "Acme", "qty": 2},
                    {"mpn": "C3", "manufacturer": "Other", "qty": 1},
                ],
                "components": [],
            },
        ]
    )

    result = service.diff(object_id, org_id, 1, 2)

    assert result["version_a"] == 1
    assert result["version_b"] == 2
    assert len(result["removed"]) == 1
    assert result["removed"][0]["mpn"] == "R2"
    assert len(result["added"]) == 1
    assert result["added"][0]["mpn"] == "C3"
    assert len(result["changed"]) == 1
    assert result["changed"][0]["before"]["qty"] == 1
    assert result["changed"][0]["after"]["qty"] == 2
