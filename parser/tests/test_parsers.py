from __future__ import annotations

import io
import struct

from parser.enrichment import enqueue_octopart_enrichment, set_enrichment_handler
from parser.parsers.bom import BOMParser
from parser.parsers.firmware import FirmwareStore
from parser.parsers.gerber import GerberParser
from parser.parsers.kicad_pcb import KiCadPCBParser
from parser.parsers.kicad_sch import KiCadSchematicParser
from parser.parsers.pdf import PDFStore
from parser.parsers.raw import RawStore
from parser.parsers.step import StepParser
from parser.registry import PARSER_REGISTRY, get_parser
from parser.tests.conftest import load_fixture

OID = "00000000-0000-0000-0000-000000000001"
VID = "00000000-0000-0000-0000-000000000002"


def _parse(parser_cls, rel_path: str, filename: str | None = None):
    data = load_fixture(*rel_path.split("/"))
    name = filename or rel_path.split("/")[-1]
    return parser_cls().parse_legacy(data, name, OID, VID)


class TestKiCadPCB:
    def test_valid_extracts_board_and_components(self):
        out = _parse(KiCadPCBParser, "kicad/valid.kicad_pcb")
        assert out.parser_name == "KiCadPCBParser"
        assert out.file_type == "PCB"
        assert len(out.components) == 2
        assert out.components[0].ref == "U1"
        assert out.components[0].mpn == "STM32F405RGT6"
        assert out.board is not None
        assert out.board["net_count"] == 3
        assert out.board["layer_count"] >= 3
        assert out.board["width_mm"] == 80.0
        assert out.board["height_mm"] == 60.0
        assert out.extracted_metadata["title"] == "HCP Test Board"

    def test_malformed_does_not_raise(self):
        out = _parse(KiCadPCBParser, "kicad/malformed.kicad_pcb")
        assert isinstance(out.errors, list)

    def test_empty_has_errors(self):
        out = _parse(KiCadPCBParser, "kicad/empty.kicad_pcb")
        assert out.errors or out.warnings


class TestKiCadSchematic:
    def test_valid_symbols(self):
        out = _parse(KiCadSchematicParser, "kicad/valid.kicad_sch")
        refs = {c.ref for c in out.components}
        assert "R1" in refs
        assert "U1" in refs
        assert out.extracted_metadata.get("hierarchical_sheets")

    def test_malformed(self):
        out = _parse(KiCadSchematicParser, "kicad/malformed.kicad_sch")
        assert out.errors or out.warnings

    def test_empty(self):
        out = _parse(KiCadSchematicParser, "kicad/empty.kicad_sch")
        assert out.errors


class TestBOM:
    def test_valid_csv(self):
        enqueued: list[str] = []
        set_enrichment_handler(lambda mpn, _vid: enqueued.append(mpn))
        try:
            out = _parse(BOMParser, "bom/valid.csv")
        finally:
            set_enrichment_handler(None)
        assert len(out.bom_rows) == 2
        assert "STM32F405RGT6" in enqueued
        assert out.bom_rows[1].mpn == "STM32F405RGT6"
        assert out.bom_rows[1].quantity == 2
        assert "U1" in out.bom_rows[1].ref_designators

    def test_malformed_csv_warns(self):
        out = _parse(BOMParser, "bom/malformed.csv")
        assert out.warnings

    def test_empty_csv(self):
        out = _parse(BOMParser, "bom/empty.csv")
        assert not out.bom_rows

    def test_valid_xlsx(self):
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.append(["Ref", "Qty", "MPN", "Manufacturer"])
        ws.append(["C1", 5, "CL10B104KA8NNNC", "Samsung"])
        buf = io.BytesIO()
        wb.save(buf)
        out = BOMParser().parse_legacy(buf.getvalue(), "bom.xlsx", OID, VID)
        assert len(out.bom_rows) == 1
        assert out.bom_rows[0].quantity == 5

    def test_octopart_enqueue_stub(self):
        seen: list[str] = []

        def handler(mpn: str, _vid: str) -> None:
            seen.append(mpn)

        set_enrichment_handler(handler)
        try:
            enqueue_octopart_enrichment(["AAA", "AAA", "BBB"], VID)
            assert seen == ["AAA", "BBB"]
        finally:
            set_enrichment_handler(None)


class TestGerber:
    def test_valid_copper(self):
        out = _parse(GerberParser, "gerber/valid.gbr")
        assert out.gerber["layer_role"] == "copper"
        assert out.gerber["file_completeness"] in ("partial", "complete", "unknown")

    def test_outline(self):
        out = _parse(GerberParser, "gerber/outline.gbr", "board.gbr")
        assert out.gerber["board_outline_present"] is True

    def test_drill(self):
        out = _parse(GerberParser, "gerber/drill.drl")
        assert out.gerber["drill_files"]

    def test_malformed_no_raise(self):
        out = _parse(GerberParser, "gerber/malformed.gbr")
        assert out.gerber is not None

    def test_empty(self):
        out = _parse(GerberParser, "gerber/empty.gbr")
        assert out.gerber is not None


class TestStep:
    def test_valid_bbox(self):
        out = _parse(StepParser, "step/valid.step")
        bbox = out.mechanical["bounding_box_mm"]
        assert bbox["x"] == 100.0
        assert bbox["y"] == 80.0
        assert bbox["z"] == 50.0

    def test_malformed_degrades(self):
        out = _parse(StepParser, "step/malformed.step")
        assert out.mechanical is not None

    def test_empty(self):
        out = _parse(StepParser, "step/empty.step")
        assert out.mechanical is not None


class TestFirmware:
    def _elf_arm(self) -> bytes:
        hdr = bytearray(52)
        hdr[0:4] = b"\x7fELF"
        hdr[4] = 1  # 32-bit
        hdr[5] = 1  # little endian
        struct.pack_into("<H", hdr, 18, 40)  # EM_ARM
        return bytes(hdr)

    def test_elf_arch(self):
        out = FirmwareStore().parse_legacy(self._elf_arm(), "fw.elf", OID, VID)
        assert out.firmware["target_arch"] == "ARM"
        assert out.firmware["format"] == "ELF"

    def test_hex_bin(self):
        for name in ("a.hex", "a.bin"):
            out = FirmwareStore().parse_legacy(b"\x00\x01", name, OID, VID)
            assert out.firmware["size_bytes"] == 2

    def test_uf2_header(self):
        data = b"UF2\n\x00" + b"\x00" * 23 + struct.pack("<I", 0xE48BFF56)
        out = FirmwareStore().parse_legacy(data, "fw.uf2", OID, VID)
        assert out.firmware["format"] == "UF2"


class TestRawAndRegistry:
    def test_rawstore_never_fails(self):
        out = RawStore().parse_legacy(b"", "unknown.xyz", OID, VID)
        assert out.parser_name == "RawStore"
        assert "sha256" in out.extracted_metadata

    def test_registry_kicad(self):
        assert isinstance(get_parser("board.kicad_pcb"), KiCadPCBParser)

    def test_registry_fallback(self):
        assert isinstance(get_parser("file.unknown"), RawStore)

    def test_registry_has_catchall(self):
        assert PARSER_REGISTRY["*"] is RawStore

    def test_pdf(self):
        out = PDFStore().parse_legacy(b"%PDF-1.4", "doc.pdf", OID, VID)
        assert out.file_type == "PDF"
