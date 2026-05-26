from __future__ import annotations

from app.services.object_types import (
    infer_domain,
    infer_object_type,
    infer_representation,
)


def test_infer_representation_native_and_interchange():
    assert infer_representation("pcb.kicad_pcb") == "native"
    assert infer_representation("part.sldprt") == "native"
    assert infer_representation("export.step") == "interchange"
    assert infer_representation("bom.csv") == "interchange"
    assert infer_representation("custom.dat", representation="derived") == "derived"


def test_infer_domain_by_extension_and_tool():
    assert infer_domain("board.gbr") == "manufacturing"
    assert infer_domain("assy.stp") == "mechanical"
    assert infer_domain("fw.hex") == "firmware"
    assert infer_domain("doc.pdf") == "document"
    assert infer_domain("x.unknown", source_tool="Fusion360") == "mechanical"
    assert infer_domain("x.unknown", domain="electrical") == "electrical"


def test_infer_object_type_respects_domain():
    assert infer_object_type("x.hex") == "FIRMWARE"
    assert infer_object_type("x.csv") == "BOM"
    assert infer_object_type("x.unknown", domain="mechanical") == "STEP"
