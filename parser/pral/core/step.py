from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path

from parser.pral.core.base import BaseParser
from parser.schema import ParsedOutput
from parser.pral.interfaces.parser_plugin import ParseContext, apply_capabilities

_PARSE_TIMEOUT_SEC = 60


class StepParser(BaseParser):
    parser_name = "StepParser"
    file_type = "STEP"

    def parse(self, file_bytes: bytes, context: ParseContext) -> ParsedOutput:
        output = self._base_output(context)
        output.parser_version = "1.0.0"
        ext = Path(context.filename).suffix.lower()
        output.tool_name = "STEP"

        output.source_tool = "STEP" if ext in (".step", ".stp") else "STL"

        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(_extract_mechanical, file_bytes, context.filename)
                mechanical, meta, warnings = future.result(timeout=_PARSE_TIMEOUT_SEC)
            output.mechanical = mechanical
            output.extracted_metadata.update(meta)
            output.warnings.extend(warnings)
        except FuturesTimeoutError:
            output.warnings.append(
                f"parse timed out after {_PARSE_TIMEOUT_SEC}s; degraded metadata only"
            )
            output.mechanical = _degraded_mechanical(file_bytes)
            output.extracted_metadata["timeout"] = True
        except Exception as exc:  # noqa: BLE001
            output.errors.append(f"parse error: {exc}")
            output.mechanical = _degraded_mechanical(file_bytes)

        return apply_capabilities(output)


def _extract_mechanical(
    file_bytes: bytes, filename: str
) -> tuple[dict, dict[str, str | float | int | None], list[str]]:
    warnings: list[str] = []
    text = file_bytes.decode("utf-8", errors="replace")
    if not text.strip():
        text = file_bytes.decode("latin-1", errors="replace")

    if "ISO-10303" not in text[:200] and filename.lower().endswith(".stl"):
        return _stl_metadata(file_bytes), {"format": "STL"}, warnings

    xs, ys, zs = _cartesian_points(text)
    bbox = None
    if xs and ys and zs:
        bbox = {
            "x": round(max(xs) - min(xs), 4),
            "y": round(max(ys) - min(ys), 4),
            "z": round(max(zs) - min(zs), 4),
        }

    products = len(re.findall(r"\bPRODUCT\s*\(", text))
    materials = list(
        {m.group(1) for m in re.finditer(r"'([A-Za-z][^']{2,30})'", text[:50000])}
    )[:5]

    mechanical = {
        "bounding_box_mm": bbox,
        "volume_cm3": None,
        "surface_area_cm2": None,
        "subassembly_count": max(products, 1),
        "material_hints": materials[:5],
    }
    meta = {
        "format": "STEP",
        "file_name": _step_string(text, "FILE_NAME"),
        "description": _step_string(text, "FILE_DESCRIPTION"),
    }
    if not bbox:
        warnings.append("could not compute bounding box from CARTESIAN_POINT entities")
    return mechanical, meta, warnings


def _cartesian_points(text: str) -> tuple[list[float], list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    for m in re.finditer(
        r"CARTESIAN_POINT\s*\([^)]*?\(([-\d.eE+]+)\s*,\s*([-\d.eE+]+)\s*,\s*([-\d.eE+]+)\)",
        text,
    ):
        try:
            xs.append(float(m.group(1)))
            ys.append(float(m.group(2)))
            zs.append(float(m.group(3)))
        except ValueError:
            continue
    if not xs:
        for m in re.finditer(
            r"CARTESIAN_POINT\s*\(\s*'[^']*'\s*,\s*\(([-\d.eE+]+)\s*,\s*([-\d.eE+]+)\s*,\s*([-\d.eE+]+)\)",
            text,
        ):
            try:
                xs.append(float(m.group(1)))
                ys.append(float(m.group(2)))
                zs.append(float(m.group(3)))
            except ValueError:
                continue
    return xs, ys, zs


def _step_string(text: str, entity: str) -> str | None:
    m = re.search(rf"{entity}\s*\(\s*'([^']*)'", text)
    return m.group(1) if m else None


def _degraded_mechanical(file_bytes: bytes) -> dict:
    return {
        "bounding_box_mm": None,
        "volume_cm3": None,
        "surface_area_cm2": None,
        "subassembly_count": None,
        "material_hints": [],
        "size_bytes": len(file_bytes),
    }


def _stl_metadata(file_bytes: bytes) -> dict:
    return {
        "bounding_box_mm": None,
        "volume_cm3": None,
        "surface_area_cm2": None,
        "subassembly_count": 1,
        "material_hints": [],
        "format": "STL",
        "size_bytes": len(file_bytes),
    }
