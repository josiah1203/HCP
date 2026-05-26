from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path

import yaml

from parser.pral.interfaces.converter import Converter
from parser.pral.interfaces.parser_plugin import ParserPlugin

_PLUGINS_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class PluginManifest:
    id: str
    vendor: str
    domains: list[str]
    extensions: list[str]
    requires_sidecar: bool
    output_capabilities: list[str]
    source_tools: list[str]


@dataclass
class LoadedPlugin:
    manifest: PluginManifest
    parser_cls: type[ParserPlugin]
    converter_cls: type[Converter] | None
    source_tools: list[str]
    extensions: list[str]

    def __call__(self) -> ParserPlugin:
        return self.parser_cls()


def _load_manifest(plugin_dir: Path) -> PluginManifest:
    data = yaml.safe_load((plugin_dir / "plugin.yaml").read_text())
    return PluginManifest(
        id=data["id"],
        vendor=data["vendor"],
        domains=list(data.get("domains", [])),
        extensions=[e.lower() for e in data.get("extensions", [])],
        requires_sidecar=bool(data.get("requires_sidecar", False)),
        output_capabilities=list(data.get("output_capabilities", [])),
        source_tools=list(data.get("source_tools", [])),
    )


def _discover_plugin_dirs() -> list[Path]:
    """Scan plugins/ for plugin.yaml — no vendor SDK imports."""
    dirs: list[Path] = []
    for entry in sorted(_PLUGINS_ROOT.iterdir()):
        if not entry.is_dir() or entry.name.startswith("_"):
            continue
        if (entry / "plugin.yaml").is_file():
            dirs.append(entry)
    return dirs


def load_plugins() -> list[LoadedPlugin]:
    loaded: list[LoadedPlugin] = []
    for plugin_dir in _discover_plugin_dirs():
        manifest = _load_manifest(plugin_dir)
        module_name = f"parser.pral.plugins.{plugin_dir.name}.parser"
        mod = importlib.import_module(module_name)
        parser_cls = getattr(mod, "StubParser", None)
        if parser_cls is None:
            continue
        converter_cls: type[Converter] | None = None
        try:
            conv_mod = importlib.import_module(
                f"parser.pral.plugins.{plugin_dir.name}.converter"
            )
            converter_cls = getattr(conv_mod, "StubConverter", None)
        except ModuleNotFoundError:
            pass
        loaded.append(
            LoadedPlugin(
                manifest=manifest,
                parser_cls=parser_cls,
                converter_cls=converter_cls,
                source_tools=manifest.source_tools,
                extensions=manifest.extensions,
            )
        )
    return loaded
