from __future__ import annotations

from parser.pral.interfaces.parser_plugin import (
    ParseContext,
    ParserPlugin,
    apply_capabilities,
)
from parser.schema import ParsedOutput


class StubParser(ParserPlugin):
    parser_name = "stub_altium"
    file_type = "SCHEMATIC"

    def parse(self, file_bytes: bytes, context: ParseContext) -> ParsedOutput:
        output = self._base_output(context)
        output.source_tool = context.source_tool or "Altium"
        output.tool_name = output.source_tool
        output.domain = "electrical"
        output.representation = "native"
        output.capabilities = ["has_gerber_stack", "has_bom"]
        output.errors.append(
            "Altium native parse requires sidecar plugin; use ODB++/Gerber/BOM export for V1."
        )
        output.extracted_metadata["requires_sidecar"] = True
        output.extracted_metadata["plugin_id"] = "stub_altium"
        return apply_capabilities(output)
