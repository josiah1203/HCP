from __future__ import annotations

import struct
from pathlib import Path

from parser.pral.core.base import BaseParser
from parser.schema import ParsedOutput
from parser.pral.interfaces.parser_plugin import ParseContext, apply_capabilities

# ELF e_machine → arch label (common embedded targets)
_ELF_MACHINE: dict[int, str] = {
    3: "x86",
    62: "x86_64",
    40: "ARM",
    183: "ARM64",
    8: "MIPS",
    243: "RISCV",
    1: "AVR",
    94: "ESP32",
}


class FirmwareStore(BaseParser):
    parser_name = "FirmwareStore"
    file_type = "FIRMWARE"

    def parse(self, file_bytes: bytes, context: ParseContext) -> ParsedOutput:
        output = self._base_output(context)
        output.parser_version = "1.0.0"
        ext = Path(context.filename).suffix.lower()
        fmt = ext.lstrip(".").upper()
        if fmt == "ELF":
            fmt = "ELF"
        elif fmt in ("HEX", "BIN", "UF2"):
            pass
        else:
            fmt = ext.lstrip(".").upper() or "BIN"

        arch = "unknown"
        if ext == ".elf":
            arch = _elf_architecture(file_bytes)
        elif ext == ".uf2":
            arch = _uf2_family(file_bytes)

        output.firmware = {
            "target_arch": arch,
            "format": fmt,
            "size_bytes": len(file_bytes),
        }
        return apply_capabilities(output)


def _elf_architecture(data: bytes) -> str:
    if len(data) < 20:
        return "unknown"
    if data[:4] != b"\x7fELF":
        return "unknown"
    ei_class = data[4]
    if ei_class not in (1, 2):
        return "unknown"
    endian = "<" if data[5] == 1 else ">"
    if ei_class == 1:
        # 32-bit: e_machine at offset 18
        if len(data) < 20:
            return "unknown"
        machine = struct.unpack(f"{endian}H", data[18:20])[0]
    else:
        if len(data) < 22:
            return "unknown"
        machine = struct.unpack(f"{endian}H", data[18:20])[0]
    return _ELF_MACHINE.get(machine, "unknown")


def _uf2_family(data: bytes) -> str:
    if len(data) < 32 or data[0:4] != b"UF2\n":
        return "unknown"
    family_id = struct.unpack_from("<I", data, 28)[0]
    families = {
        0xE48BFF56: "RP2040",
        0x00FF6919: "STM32F4",
        0x16573617: "ESP32",
    }
    return families.get(family_id, "unknown")
