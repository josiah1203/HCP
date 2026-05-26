"""PrAL capability router — source_tool+ext, magic bytes, extension map, RawStore."""

from __future__ import annotations

from pathlib import Path

from parser.pral.core import (
    BOMParser,
    FirmwareStore,
    GerberParser,
    KiCadPCBParser,
    KiCadSchematicParser,
    PDFStore,
    RawStore,
    StepParser,
)
from parser.pral.interfaces.converter import Converter
from parser.pral.interfaces.parser_plugin import ParseContext, ParserPlugin
from parser.pral.plugins.loader import load_plugins

# Extension map (priority 3) — same coverage as legacy PARSER_REGISTRY
EXTENSION_REGISTRY: dict[str, type[ParserPlugin]] = {
    ".kicad_pcb": KiCadPCBParser,
    ".kicad_sch": KiCadSchematicParser,
    ".gbr": GerberParser,
    ".gtl": GerberParser,
    ".gbl": GerberParser,
    ".gts": GerberParser,
    ".gbs": GerberParser,
    ".gto": GerberParser,
    ".gbo": GerberParser,
    ".drl": GerberParser,
    ".step": StepParser,
    ".stp": StepParser,
    ".stl": StepParser,
    ".csv": BOMParser,
    ".xlsx": BOMParser,
    ".xls": BOMParser,
    ".bin": FirmwareStore,
    ".hex": FirmwareStore,
    ".elf": FirmwareStore,
    ".uf2": FirmwareStore,
    ".pdf": PDFStore,
}

_MAGIC_ROUTES: list[tuple[bytes, type[ParserPlugin]]] = [
    (b"%PDF", PDFStore),
    (b"\x7fELF", FirmwareStore),
    (b"UF2\n", FirmwareStore),
    (b"ISO-10303", StepParser),
]

_PLUGINS = load_plugins()


def _normalize_source_tool(source_tool: str | None) -> str | None:
    if not source_tool:
        return None
    return source_tool.strip()


def _match_loaded_plugin(source_tool: str | None, ext: str):
    st = _normalize_source_tool(source_tool)
    if not st:
        return None
    st_lower = st.lower()
    for plugin in _PLUGINS:
        if (
            st_lower in {t.lower() for t in plugin.source_tools}
            and ext in plugin.extensions
        ):
            return plugin
    return None


def _match_plugin(source_tool: str | None, ext: str) -> ParserPlugin | None:
    loaded = _match_loaded_plugin(source_tool, ext)
    return loaded() if loaded is not None else None


def resolve_converter(
    filename: str,
    *,
    source_tool: str | None = None,
) -> Converter | None:
    """Optional V2 converter for native files before core interchange parse."""
    ext = Path(filename).suffix.lower()
    loaded = _match_loaded_plugin(source_tool, ext)
    if loaded is None or loaded.converter_cls is None:
        return None
    return loaded.converter_cls()


def _sniff_parser(file_bytes: bytes, ext: str) -> type[ParserPlugin] | None:
    head = file_bytes[:512]
    for magic, parser_cls in _MAGIC_ROUTES:
        if magic in head:
            return parser_cls
    if ext in (".step", ".stp") and b"ISO-10303" in head:
        return StepParser
    if ext == ".drl" and (b"M48" in head or b"DRILL" in head.upper()):
        return GerberParser
    return None


def resolve_parser(
    filename: str,
    file_bytes: bytes,
    *,
    source_tool: str | None = None,
    domain: str | None = None,
    representation: str | None = None,
) -> ParserPlugin:
    ext = Path(filename).suffix.lower()
    plugin = _match_plugin(source_tool, ext)
    if plugin is not None:
        return plugin
    sniffed = _sniff_parser(file_bytes, ext)
    if sniffed is not None:
        return sniffed()
    parser_cls = EXTENSION_REGISTRY.get(ext, RawStore)
    return parser_cls()


def get_parser(
    filename: str,
    file_bytes: bytes = b"",
    *,
    source_tool: str | None = None,
    domain: str | None = None,
    representation: str | None = None,
) -> ParserPlugin:
    """Resolve parser instance for filename and optional upload metadata."""
    return resolve_parser(
        filename,
        file_bytes,
        source_tool=source_tool,
        domain=domain,
        representation=representation,
    )


def build_context(
    filename: str,
    object_id: str,
    version_id: str,
    *,
    source_tool: str | None = None,
    domain: str | None = None,
    representation: str | None = None,
) -> ParseContext:
    return ParseContext(
        filename=filename,
        object_id=object_id,
        version_id=version_id,
        source_tool=source_tool,
        domain=domain,  # type: ignore[arg-type]
        representation=representation,  # type: ignore[arg-type]
    )
