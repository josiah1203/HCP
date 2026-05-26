from __future__ import annotations
import hashlib

from parser.pral.core.base import BaseParser
from parser.schema import ParsedOutput
from parser.pral.interfaces.parser_plugin import ParseContext, apply_capabilities


class RawStore(BaseParser):
    parser_name = "RawStore"
    file_type = "OTHER"

    def parse(self, file_bytes: bytes, context: ParseContext) -> ParsedOutput:
        output = self._base_output(context)
        output.extracted_metadata["sha256"] = hashlib.sha256(file_bytes).hexdigest()
        output.extracted_metadata["size_bytes"] = len(file_bytes)
        return apply_capabilities(output)
