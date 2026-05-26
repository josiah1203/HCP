from __future__ import annotations

from parser.pral.core.base import BaseParser
from parser.pral.core.sexpr import parse_sexpr, sexpr_child, sexpr_find
from parser.schema import Component, ParsedOutput
from parser.pral.interfaces.parser_plugin import ParseContext, apply_capabilities


class KiCadPCBParser(BaseParser):
    parser_name = "KiCadPCBParser"
    file_type = "PCB"

    def parse(self, file_bytes: bytes, context: ParseContext) -> ParsedOutput:
        output = self._base_output(context)
        output.tool_name = "KiCad"

        output.source_tool = "KiCad"
        output.parser_version = "1.0.0"

        try:
            text = file_bytes.decode("utf-8", errors="replace")
            tree = parse_sexpr(text)
            if not isinstance(tree, list) or not tree or tree[0] != "kicad_pcb":
                output.errors.append("not a valid kicad_pcb file")
                return apply_capabilities(output)

            output.extracted_metadata.update(_title_block(tree))
            components = _extract_footprints(tree)
            output.components = components
            nets = sexpr_find(tree, "net")
            layers = _copper_layers(tree)
            width_mm, height_mm = _board_dimensions(tree)

            output.board = {
                "width_mm": width_mm,
                "height_mm": height_mm,
                "layer_count": len(layers),
                "net_count": len(nets),
                "copper_layers": layers,
                "min_trace_mm": None,
                "min_via_mm": None,
                "stackup": None,
            }
        except Exception as exc:  # noqa: BLE001 — graceful degrade per §9
            output.errors.append(f"parse error: {exc}")

        return apply_capabilities(output)


def _title_block(tree: list) -> dict[str, str | None]:
    meta: dict[str, str | None] = {
        "title": None,
        "revision": None,
        "author": None,
        "date": None,
        "project_name": None,
    }
    block = sexpr_child(tree, "title_block")
    if not block:
        return meta
    mapping = {
        "title": "title",
        "rev": "revision",
        "company": "author",
        "date": "date",
        "comment": "project_name",
    }
    for item in block[1:]:
        if isinstance(item, list) and len(item) >= 2 and item[0] in mapping:
            val = item[1]
            if isinstance(val, str):
                key = mapping[item[0]]
                if meta.get(key) is None or item[0] == "title":
                    meta[key] = val
    return meta


def _copper_layers(tree: list) -> list[str]:
    layers_node = sexpr_child(tree, "layers")
    if not layers_node:
        return []
    copper: list[str] = []
    for layer in layers_node[1:]:
        if not isinstance(layer, list) or len(layer) < 2:
            continue
        name = layer[1] if isinstance(layer[1], str) else None
        layer_type = layer[2] if len(layer) > 2 else None
        if name and layer_type == "signal":
            copper.append(name)
    return copper


def _extract_footprints(tree: list) -> list[Component]:
    components: list[Component] = []
    for fp in sexpr_find(tree, "footprint"):
        ref = _footprint_property(fp, "Reference")
        if not ref:
            continue
        value = _footprint_property(fp, "Value")
        footprint = fp[1] if len(fp) > 1 and isinstance(fp[1], str) else None
        mpn = _footprint_property(fp, "MPN") or value
        mfr = _footprint_property(fp, "Manufacturer")
        desc = _footprint_property(fp, "Description")
        dnp = _footprint_property(fp, "DNP") == "true"
        components.append(
            Component(
                ref=ref,
                mpn=mpn,
                manufacturer=mfr,
                value=value,
                footprint=footprint if isinstance(footprint, str) else None,
                description=desc,
                dnp=dnp,
            )
        )
    return components


def _footprint_property(fp: list, key: str) -> str | None:
    for item in fp:
        if (
            isinstance(item, list)
            and len(item) >= 3
            and item[0] == "property"
            and item[1] == key
        ):
            val = item[2]
            return val if isinstance(val, str) else None
    return None


def _board_dimensions(tree: list) -> tuple[float | None, float | None]:
    xs: list[float] = []
    ys: list[float] = []
    for node in sexpr_find(tree, "gr_rect") + sexpr_find(tree, "gr_line"):
        layer = _node_layer(node)
        if layer and "Edge.Cuts" not in layer and "Dwgs.User" not in layer:
            if node[0] != "gr_rect" and layer != "Edge.Cuts":
                continue
        _collect_points(node, xs, ys)
    if xs and ys:
        return round(max(xs) - min(xs), 4), round(max(ys) - min(ys), 4)
    general = sexpr_child(tree, "general")
    if general:
        for item in general[1:]:
            if isinstance(item, list) and item[0] == "board_thickness":
                pass
    return None, None


def _node_layer(node: list) -> str | None:
    for item in node:
        if isinstance(item, list) and item and item[0] == "layer" and len(item) > 1:
            return item[1] if isinstance(item[1], str) else None
    return None


def _collect_points(node: list, xs: list[float], ys: list[float]) -> None:
    for i, item in enumerate(node):
        if item in ("start", "end", "at", "xy") and i + 2 < len(node):
            x, y = node[i + 1], node[i + 2]
            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                xs.append(float(x))
                ys.append(float(y))
        elif isinstance(item, list):
            _collect_points(item, xs, ys)
