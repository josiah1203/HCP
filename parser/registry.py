"""Legacy registry shim — delegates to PrAL."""

from __future__ import annotations

from parser.pral.core.raw import RawStore
from parser.pral.interfaces.parser_plugin import ParserPlugin
from parser.pral.registry import EXTENSION_REGISTRY, get_parser as pral_get_parser

# Backward-compatible alias for tests
PARSER_REGISTRY: dict[str, type[ParserPlugin]] = {
    **{k: v for k, v in EXTENSION_REGISTRY.items()},
    "*": RawStore,
}


def get_parser(filename: str, file_bytes: bytes = b"") -> ParserPlugin:
    return pral_get_parser(filename, file_bytes)


def get_parser_for_extension(ext: str) -> type[ParserPlugin]:
    return PARSER_REGISTRY.get(ext.lower(), PARSER_REGISTRY["*"])
