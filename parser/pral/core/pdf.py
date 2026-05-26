from __future__ import annotations

from parser.pral.core.base import BaseParser
from parser.schema import ParsedOutput
from parser.pral.interfaces.parser_plugin import ParseContext, apply_capabilities


class PDFStore(BaseParser):
    parser_name = "PDFStore"
    file_type = "PDF"

    def parse(self, file_bytes: bytes, context: ParseContext) -> ParsedOutput:
        output = self._base_output(context)
        output.parser_version = "1.0.0"
        output.extracted_metadata["size_bytes"] = len(file_bytes)
        if not file_bytes.startswith(b"%PDF"):
            output.warnings.append("missing PDF magic header")
        return apply_capabilities(output)
