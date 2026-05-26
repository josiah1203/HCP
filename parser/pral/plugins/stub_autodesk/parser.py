from __future__ import annotations

from parser.pral.interfaces.parser_plugin import (
    ParseContext,
    ParserPlugin,
    apply_capabilities,
)
from parser.schema import ParsedOutput


class StubParser(ParserPlugin):
    parser_name = "stub_autodesk"
    file_type = "STEP"

    def parse(self, file_bytes: bytes, context: ParseContext) -> ParsedOutput:
        output = self._base_output(context)
        output.source_tool = context.source_tool or "Fusion360"
        output.tool_name = output.source_tool
        output.domain = "mechanical"
        output.representation = "native"
        output.capabilities = ["has_geometry"]
        output.errors.append(
            "Autodesk native parse requires sidecar plugin; export STEP for V1 interchange parse."
        )
        output.extracted_metadata["requires_sidecar"] = True
        output.extracted_metadata["plugin_id"] = "stub_autodesk"
        return apply_capabilities(output)
