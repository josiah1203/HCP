from __future__ import annotations

from pathlib import Path

DOMAIN_VALUES = frozenset(
    {"electrical", "mechanical", "manufacturing", "firmware", "document"}
)
REPRESENTATION_VALUES = frozenset({"native", "interchange", "derived"})

EXTENSION_TO_TYPE: dict[str, str] = {
    ".kicad_pcb": "PCB",
    ".kicad_sch": "SCHEMATIC",
    ".step": "STEP",
    ".stp": "STEP",
    ".stl": "STEP",
    ".gbr": "GERBER_STACK",
    ".gtl": "GERBER_STACK",
    ".gbl": "GERBER_STACK",
    ".gts": "GERBER_STACK",
    ".gbs": "GERBER_STACK",
    ".gto": "GERBER_STACK",
    ".gbo": "GERBER_STACK",
    ".drl": "GERBER_STACK",
    ".csv": "BOM",
    ".xlsx": "BOM",
    ".xls": "BOM",
    ".bin": "FIRMWARE",
    ".hex": "FIRMWARE",
    ".elf": "FIRMWARE",
    ".uf2": "FIRMWARE",
    ".pdf": "PDF",
}

NATIVE_EXTENSIONS = frozenset(
    {
        ".kicad_pcb",
        ".kicad_sch",
        ".sldprt",
        ".sldasm",
        ".f3d",
        ".ipt",
        ".iam",
        ".SchDoc",
        ".brd",
        ".opj",
    }
)

INTERCHANGE_EXTENSIONS = frozenset(
    {
        ".step",
        ".stp",
        ".stl",
        ".gbr",
        ".gtl",
        ".gbl",
        ".gts",
        ".gbs",
        ".gto",
        ".gbo",
        ".drl",
        ".csv",
        ".xlsx",
        ".xls",
        ".odb",
    }
)

DOMAIN_EXTENSION_HINTS: dict[str, frozenset[str]] = {
    "electrical": frozenset(
        {".kicad_pcb", ".kicad_sch", ".SchDoc", ".brd", ".opj", ".csv", ".xlsx", ".xls"}
    ),
    "mechanical": frozenset(
        {".step", ".stp", ".stl", ".sldprt", ".sldasm", ".f3d", ".ipt", ".iam"}
    ),
    "manufacturing": frozenset(
        {".gbr", ".gtl", ".gbl", ".gts", ".gbs", ".gto", ".gbo", ".drl", ".odb"}
    ),
    "firmware": frozenset({".bin", ".hex", ".elf", ".uf2"}),
    "document": frozenset({".pdf"}),
}

SOURCE_TOOL_DOMAIN_HINTS: dict[str, str] = {
    "kicad": "electrical",
    "altium": "electrical",
    "eagle": "electrical",
    "orcad": "electrical",
    "solidworks": "mechanical",
    "fusion360": "mechanical",
    "autodesk": "mechanical",
    "inventor": "mechanical",
}


def _normalize_ext(filename: str) -> str:
    return Path(filename).suffix.lower()


def infer_representation(
    filename: str,
    *,
    representation: str | None = None,
) -> str:
    if representation and representation in REPRESENTATION_VALUES:
        return representation
    ext = _normalize_ext(filename)
    if ext in NATIVE_EXTENSIONS:
        return "native"
    if ext in INTERCHANGE_EXTENSIONS:
        return "interchange"
    return "native"


def infer_domain(
    filename: str,
    mime: str | None = None,
    source_tool: str | None = None,
    *,
    domain: str | None = None,
) -> str:
    if domain and domain in DOMAIN_VALUES:
        return domain
    if source_tool:
        key = source_tool.strip().lower().replace(" ", "")
        if key in SOURCE_TOOL_DOMAIN_HINTS:
            return SOURCE_TOOL_DOMAIN_HINTS[key]
    ext = _normalize_ext(filename)
    for domain_name, extensions in DOMAIN_EXTENSION_HINTS.items():
        if ext in extensions:
            return domain_name
    if mime:
        if "firmware" in mime or mime.startswith("application/octet-stream"):
            ext = _normalize_ext(filename)
            if ext in DOMAIN_EXTENSION_HINTS["firmware"]:
                return "firmware"
        if mime == "application/pdf":
            return "document"
    return "document"


def infer_object_type(
    filename: str,
    *,
    domain: str | None = None,
    mime: str | None = None,
    source_tool: str | None = None,
) -> str:
    ext = _normalize_ext(filename)
    if ext in EXTENSION_TO_TYPE:
        return EXTENSION_TO_TYPE[ext]
    resolved_domain = infer_domain(filename, mime, source_tool, domain=domain)
    if resolved_domain == "firmware":
        return "FIRMWARE"
    if resolved_domain == "manufacturing" and ext in {".zip", ".tar", ".tgz"}:
        return "GERBER_STACK"
    if resolved_domain == "mechanical":
        return "STEP"
    if resolved_domain == "electrical":
        return "BOM" if ext in {".csv", ".xlsx", ".xls"} else "OTHER"
    return "OTHER"


def build_storage_key(
    org_id: str, project_id: str, object_id: str, version_num: int, filename: str
) -> str:
    return f"{org_id}/{project_id}/{object_id}/v{version_num}/raw/{filename}"


def build_hcp_uri(
    org_id: str, project_id: str, object_id: str, version_num: int
) -> str:
    return f"hcp://{org_id}/{project_id}/{object_id}/{version_num}"
