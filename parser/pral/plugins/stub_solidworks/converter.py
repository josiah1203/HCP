"""SolidWorks native → interchange converter stub (sidecar in V2)."""

from __future__ import annotations

from parser.pral.interfaces.converter import ConvertResult, Converter


class StubConverter(Converter):
    converter_name = "stub_solidworks_converter"

    def convert(
        self, file_bytes: bytes, filename: str, source_tool: str
    ) -> ConvertResult:
        raise NotImplementedError(
            "SolidWorks conversion requires sidecar plugin (see docs/parser-plugins.md); "
            "upload STEP interchange for V1."
        )
