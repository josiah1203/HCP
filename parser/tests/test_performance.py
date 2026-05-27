from __future__ import annotations

import time

from parser.parsers.kicad_pcb import KiCadPCBParser
from parser.tests.helpers import kicad_pcb_with_footprints

OID = "00000000-0000-0000-0000-000000000001"
VID = "00000000-0000-0000-0000-000000000002"


class TestKiCadPerformance:
    def test_1000_components_under_30_seconds(self):
        data = kicad_pcb_with_footprints(1000)
        parser = KiCadPCBParser()
        started = time.perf_counter()
        out = parser.parse_legacy(data, "large.kicad_pcb", OID, VID)
        elapsed = time.perf_counter() - started

        assert len(out.components) == 1000
        assert out.board is not None
        assert elapsed < 30.0, f"parse took {elapsed:.2f}s (gate: <30s)"
