from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from parser.pral.interfaces.converter import ConvertResult
from parser.pral.interfaces.parser_plugin import (
    ParseContext,
    infer_domain,
    infer_representation,
)
from parser.pral.plugins.loader import load_plugins
from parser.pral.plugins.stub_solidworks.converter import (
    StubConverter as SolidWorksConverter,
)
from parser.pral.registry import get_parser, resolve_converter, resolve_parser
from parser.pral.core.raw import RawStore
from parser.pral.plugins.stub_solidworks.parser import StubParser as SolidWorksStub
from parser.schema import ParsedOutput, SourceAsset

OID = "00000000-0000-0000-0000-000000000001"
VID = "00000000-0000-0000-0000-000000000002"


class TestParsedOutput11:
    def test_defaults_schema_version(self):
        out = ParsedOutput(
            object_id=OID,
            version_id=VID,
            parsed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            parser_name="RawStore",
            file_type="OTHER",
        )
        assert out.schema_version == "1.1"
        assert out.domain is None
        assert out.capabilities == []

    def test_optional_fields_roundtrip(self):
        out = ParsedOutput(
            object_id=OID,
            version_id=VID,
            parsed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            parser_name="KiCadPCBParser",
            file_type="PCB",
            domain="electrical",
            representation="native",
            source_tool="KiCad",
            source_format=".kicad_pcb",
            capabilities=["has_components"],
            source_assets=[SourceAsset(uri="hcp://v/native", role="native")],
        )
        data = out.model_dump()
        assert data["domain"] == "electrical"
        assert data["source_assets"][0]["role"] == "native"

    def test_invalid_domain_rejected(self):
        with pytest.raises(ValidationError):
            ParsedOutput(
                object_id=OID,
                version_id=VID,
                parsed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                parser_name="x",
                file_type="OTHER",
                domain="invalid",  # type: ignore[arg-type]
            )


class TestInference:
    def test_step_is_interchange(self):
        assert infer_representation(".step") == "interchange"

    def test_kicad_is_native(self):
        assert infer_representation(".kicad_pcb") == "native"

    def test_gerber_domain(self):
        assert infer_domain(".gbr", None) == "manufacturing"


class TestPrALRouting:
    def test_extension_kicad(self):
        p = get_parser("board.kicad_pcb")
        assert p.parser_name == "KiCadPCBParser"

    def test_extension_fallback_rawstore(self):
        p = get_parser("file.unknown")
        assert isinstance(p, RawStore)

    def test_magic_pdf(self):
        p = resolve_parser("x.bin", b"%PDF-1.4 fake")
        assert p.parser_name == "PDFStore"

    def test_magic_elf(self):
        p = resolve_parser("fw.bin", b"\x7fELF\x01\x01")
        assert p.parser_name == "FirmwareStore"

    def test_source_tool_routes_solidworks_stub(self):
        p = resolve_parser("part.sldprt", b"\x00", source_tool="SolidWorks")
        assert p.parser_name == "stub_solidworks"

    def test_source_tool_routes_altium_stub(self):
        p = resolve_parser("board.SchDoc", b"\x00", source_tool="Altium")
        assert p.parser_name == "stub_altium"

    def test_stub_emits_sidecar_metadata(self):
        ctx = ParseContext(
            filename="a.sldprt", object_id=OID, version_id=VID, source_tool="SolidWorks"
        )
        out = SolidWorksStub().parse(b"", ctx)
        assert out.schema_version == "1.1"
        assert out.source_tool == "SolidWorks"
        assert out.extracted_metadata.get("requires_sidecar") is True
        assert out.errors


class TestPluginLoader:
    def test_discovers_stub_plugins_from_yaml(self):
        plugins = load_plugins()
        ids = {p.manifest.id for p in plugins}
        assert ids >= {"stub_solidworks", "stub_altium", "stub_autodesk"}

    def test_manifest_extensions_lowercase(self):
        sw = next(p for p in load_plugins() if p.manifest.id == "stub_solidworks")
        assert ".sldprt" in sw.extensions


class TestConverter:
    def test_convert_result_fields(self):
        result = ConvertResult(
            data=b"ISO-10303-21;",
            target_extension=".step",
            target_filename="part.step",
            source_tool="SolidWorks",
        )
        assert result.representation == "derived"

    def test_resolve_converter_solidworks(self):
        conv = resolve_converter("part.sldprt", source_tool="SolidWorks")
        assert conv is not None
        assert conv.converter_name == "stub_solidworks_converter"

    def test_resolve_converter_none_without_source_tool(self):
        assert resolve_converter("part.sldprt") is None

    def test_stub_converter_requires_sidecar(self):
        conv = SolidWorksConverter()
        with pytest.raises(NotImplementedError, match="sidecar"):
            conv.convert(b"\x00", "part.sldprt", "SolidWorks")
