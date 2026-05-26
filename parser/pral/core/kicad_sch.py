from __future__ import annotations

from parser.pral.core.base import BaseParser
from parser.pral.core.sexpr import parse_sexpr, sexpr_find
from parser.schema import Component, ParsedOutput
from parser.pral.interfaces.parser_plugin import ParseContext, apply_capabilities


class KiCadSchematicParser(BaseParser):
    parser_name = "KiCadSchematicParser"
    file_type = "SCHEMATIC"

    def parse(self, file_bytes: bytes, context: ParseContext) -> ParsedOutput:
        output = self._base_output(context)
        output.tool_name = "KiCad"

        output.source_tool = "KiCad"
        output.parser_version = "1.0.0"

        try:
            text = file_bytes.decode("utf-8", errors="replace")
            tree = parse_sexpr(text)
            if not isinstance(tree, list) or not tree:
                output.errors.append("empty or invalid schematic")
                return apply_capabilities(output)

            root = tree[0]
            if root not in ("kicad_sch", "eeschema_schematic"):
                output.warnings.append(f"unexpected root: {root}")

            symbols = _extract_symbols(tree)
            sheets = _extract_sheets(tree)
            output.components = symbols
            output.extracted_metadata["hierarchical_sheets"] = sheets
            output.extracted_metadata["symbol_count"] = len(symbols)
            output.extracted_metadata.update(_schematic_title(tree))
        except Exception as exc:  # noqa: BLE001
            output.errors.append(f"parse error: {exc}")

        return apply_capabilities(output)


def _extract_symbols(tree: list) -> list[Component]:
    components: list[Component] = []
    for sym in sexpr_find(tree, "symbol"):
        ref = _symbol_property(sym, "Reference")
        if not ref:
            lib_id = sym[1] if len(sym) > 1 and isinstance(sym[1], str) else "unknown"
            ref = lib_id
        value = _symbol_property(sym, "Value")
        mpn = _symbol_property(sym, "MPN") or value
        components.append(
            Component(
                ref=ref,
                mpn=mpn,
                manufacturer=_symbol_property(sym, "Manufacturer"),
                value=value,
                description=_symbol_property(sym, "Description"),
            )
        )
    return components


def _extract_sheets(tree: list) -> list[dict[str, str]]:
    sheets: list[dict[str, str]] = []
    for sheet in sexpr_find(tree, "sheet"):
        name = None
        path = None
        for item in sheet[1:]:
            if isinstance(item, list) and len(item) >= 2:
                if item[0] == "uuid" and isinstance(item[1], str):
                    path = item[1]
                if item[0] in ("sheetname", "name") and isinstance(item[1], str):
                    name = item[1]
        sheets.append({"name": name or "sheet", "path": path or ""})
    return sheets


def _symbol_property(sym: list, key: str) -> str | None:
    for item in sym:
        if isinstance(item, list) and len(item) >= 3:
            if item[0] == "property" and item[1] == key:
                return item[2] if isinstance(item[2], str) else None
            if item[0] == "pin" and len(item) > 1:
                continue
    for item in sym:
        if isinstance(item, list):
            found = _symbol_property(item, key)
            if found:
                return found
    return None


def _schematic_title(tree: list) -> dict[str, str | None]:
    meta: dict[str, str | None] = {"title": None, "revision": None, "date": None}
    for block in sexpr_find(tree, "title_block"):
        for item in block[1:]:
            if isinstance(item, list) and len(item) >= 2:
                if item[0] == "title" and isinstance(item[1], str):
                    meta["title"] = item[1]
                if item[0] == "rev" and isinstance(item[1], str):
                    meta["revision"] = item[1]
                if item[0] == "date" and isinstance(item[1], str):
                    meta["date"] = item[1]
    return meta
