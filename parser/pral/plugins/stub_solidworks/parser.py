from __future__ import annotations

from parser.pral.interfaces.parser_plugin import (
    ParseContext,
    ParserPlugin,
    apply_capabilities,
)
from parser.schema import ParsedOutput


class StubParser(ParserPlugin):
    parser_name = "stub_solidworks"
    file_type = "STEP"

    def parse(self, file_bytes: bytes, context: ParseContext) -> ParsedOutput:
        output = self._base_output(context)
        output.source_tool = context.source_tool or "SolidWorks"
        output.tool_name = output.source_tool
        output.domain = "mechanical"
        output.representation = "native"
        output.capabilities = ["has_geometry"]
        output.errors.append(
            "SolidWorks native parse requires sidecar plugin (see docs/parser-plugins.md); "
            "upload STEP interchange for V1 parse."
        )
        output.extracted_metadata["requires_sidecar"] = True
        output.extracted_metadata["plugin_id"] = "stub_solidworks"
        return apply_capabilities(output)
