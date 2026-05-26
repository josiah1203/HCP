from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from parser.schema import Domain, ParsedOutput, Representation


@dataclass(frozen=True)
class ParseContext:
    filename: str
    object_id: str
    version_id: str
    source_tool: str | None = None
    domain: Domain | None = None
    representation: Representation | None = None


class ParserPlugin(ABC):
    """Contract for core parsers and optional vendor plugins."""

    parser_name: str = "BaseParser"
    file_type: str = "OTHER"

    @abstractmethod
    def parse(self, file_bytes: bytes, context: ParseContext) -> ParsedOutput:
        pass

    def parse_legacy(
        self, file_bytes: bytes, filename: str, object_id: str, version_id: str
    ) -> ParsedOutput:
        """Backward-compatible entry point used by tests and old call sites."""
        return self.parse(
            file_bytes,
            ParseContext(filename=filename, object_id=object_id, version_id=version_id),
        )

    def _base_output(self, context: ParseContext) -> ParsedOutput:
        ext = Path(context.filename).suffix.lower()
        rep = context.representation or infer_representation(ext)
        dom = context.domain or infer_domain(ext, context.source_tool)
        tool = context.source_tool or "Unknown"
        return ParsedOutput(
            schema_version="1.1",
            object_id=context.object_id,
            version_id=context.version_id,
            parsed_at=datetime.now(timezone.utc),
            parser_name=self.parser_name,
            file_type=self.file_type,
            tool_name=tool if tool != "Unknown" else "Unknown",
            source_tool=context.source_tool,
            source_format=ext or None,
            domain=dom,
            representation=rep,
            extracted_metadata={"filename": context.filename},
        )


INTERCHANGE_EXTENSIONS = {
    ".step",
    ".stp",
    ".stl",
    ".gbr",
    ".gtl",
    ".gbl",
    ".gts",
    ".gbs",
    ".gto",
    ".gbo",
    ".drl",
    ".csv",
    ".xlsx",
    ".xls",
}

NATIVE_EXTENSIONS = {
    ".kicad_pcb",
    ".kicad_sch",
    ".sldprt",
    ".sldasm",
    ".slddrw",
    ".schdoc",
    ".brd",
    ".f3d",
    ".ipt",
}


def infer_representation(ext: str) -> Representation:
    if ext in INTERCHANGE_EXTENSIONS:
        return "interchange"
    if ext in NATIVE_EXTENSIONS:
        return "native"
    if ext in {".bin", ".hex", ".elf", ".uf2", ".pdf"}:
        return "native"
    return "native"


def infer_domain(ext: str, source_tool: str | None) -> Domain | None:
    if source_tool:
        st = source_tool.lower()
        if st in ("solidworks", "fusion360", "autodesk", "inventor"):
            return "mechanical"
        if st in ("altium", "eagle", "orcad", "kicad"):
            return "electrical"
    if ext in (".kicad_pcb", ".kicad_sch", ".schdoc", ".brd", ".csv", ".xlsx", ".xls"):
        return "electrical"
    if ext in (".step", ".stp", ".stl", ".sldprt", ".sldasm", ".f3d", ".ipt"):
        return "mechanical"
    if ext in (".gbr", ".gtl", ".gbl", ".gts", ".gbs", ".gto", ".gbo", ".drl"):
        return "manufacturing"
    if ext in (".bin", ".hex", ".elf", ".uf2"):
        return "firmware"
    if ext == ".pdf":
        return "document"
    return None


def apply_capabilities(output: ParsedOutput) -> ParsedOutput:
    caps: list[str] = []
    if output.bom_rows:
        caps.append("has_bom")
    if output.components:
        caps.append("has_components")
    if output.mechanical or (output.board and output.board.get("width_mm")):
        caps.append("has_geometry")
    if output.gerber:
        caps.append("has_gerber_stack")
    if output.firmware:
        caps.append("has_firmware")
    output.capabilities = sorted(set(output.capabilities) | set(caps))
    return output
