"""Native → interchange conversion contract (V2 plugins)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ConvertResult:
    """Output of a vendor converter before core parser runs."""

    data: bytes
    target_extension: str
    target_filename: str
    source_tool: str
    representation: str = "derived"


class Converter(ABC):
    """Optional second stage: proprietary bytes → STEP/Gerber/BOM bytes."""

    converter_name: str = "BaseConverter"

    @abstractmethod
    def convert(
        self, file_bytes: bytes, filename: str, source_tool: str
    ) -> ConvertResult:
        pass
