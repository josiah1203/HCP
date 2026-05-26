from __future__ import annotations

import re
from pathlib import Path

from parser.pral.core.base import BaseParser
from parser.schema import ParsedOutput
from parser.pral.interfaces.parser_plugin import ParseContext, apply_capabilities

_LAYER_SUFFIXES = {
    ".gtl": "top_copper",
    ".gbl": "bottom_copper",
    ".gts": "top_mask",
    ".gbs": "bottom_mask",
    ".gto": "top_silk",
    ".gbo": "bottom_silk",
    ".gbr": "copper",
    ".drl": "drill",
}


class GerberParser(BaseParser):
    parser_name = "GerberParser"
    file_type = "GERBER_STACK"

    def parse(self, file_bytes: bytes, context: ParseContext) -> ParsedOutput:
        output = self._base_output(context)
        output.parser_version = "1.0.0"

        try:
            text = file_bytes.decode("utf-8", errors="replace")
            ext = Path(context.filename).suffix.lower()
            layer_role = _LAYER_SUFFIXES.get(ext, "unknown")
            is_drill = (
                ext == ".drl" or "M48" in text[:500] or "DRILL" in text.upper()[:200]
            )
            outline = _detect_outline(text, ext)
            layer_name = _extract_layer_name(text) or context.filename

            layer_files = [context.filename]
            drill_files = [context.filename] if is_drill else []
            completeness = _assess_completeness(is_drill, outline, layer_role)

            output.gerber = {
                "layer_files": layer_files,
                "drill_files": drill_files,
                "board_outline_present": outline,
                "file_completeness": completeness,
                "layer_name": layer_name,
                "layer_role": layer_role,
            }
            output.extracted_metadata["format"] = (
                "excellon" if is_drill else "gerber-x2" if "%TF" in text else "gerber"
            )
        except Exception as exc:  # noqa: BLE001
            output.errors.append(f"parse error: {exc}")

        return apply_capabilities(output)


def _extract_layer_name(text: str) -> str | None:
    m = re.search(r"%TF\.FileFunction,([^*%)]+)", text)
    if m:
        return m.group(1).strip()
    m = re.search(r"G04\s+Layer:\s*(.+)", text)
    if m:
        return m.group(1).strip()
    return None


def _detect_outline(text: str, ext: str) -> bool:
    if "outline" in text.lower()[:500]:
        return True
    if re.search(r"%TF\.FileFunction,.*outline", text, re.I):
        return True
    if "G36" in text and "G37" in text:
        return True
    if ext in (".gko", ".gm1"):
        return True
    return False


def _assess_completeness(is_drill: bool, outline: bool, layer_role: str) -> str:
    if is_drill:
        return "partial"
    if outline:
        return "partial"
    if layer_role in ("top_copper", "bottom_copper", "copper"):
        return "partial"
    return "unknown"
