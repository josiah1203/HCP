"""Canonical ParsedOutput schema — contract between parser and downstream services."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Domain = Literal["electrical", "mechanical", "manufacturing", "firmware", "document"]
Representation = Literal["native", "interchange", "derived"]


class Component(BaseModel):
    ref: str
    mpn: str | None = None
    manufacturer: str | None = None
    value: str | None = None
    footprint: str | None = None
    description: str | None = None
    quantity: int = 1
    dnp: bool = False


class BOMRow(BaseModel):
    ref_designators: list[str] = Field(default_factory=list)
    mpn: str | None = None
    manufacturer: str | None = None
    quantity: int = 1
    description: str | None = None
    unit_price_usd: float | None = None


class SourceAsset(BaseModel):
    """Link to related stored artifact (native ↔ interchange / derived)."""

    uri: str
    role: str


class ParsedOutput(BaseModel):
    schema_version: str = "1.1"
    object_id: str
    version_id: str
    parsed_at: datetime
    parser_name: str
    parser_version: str = "0.1.0"
    file_type: str
    tool_name: str = "Unknown"
    tool_version: str | None = None
    components: list[Component] = Field(default_factory=list)
    bom_rows: list[BOMRow] = Field(default_factory=list)
    board: dict[str, Any] | None = None
    mechanical: dict[str, Any] | None = None
    gerber: dict[str, Any] | None = None
    firmware: dict[str, Any] | None = None
    extracted_metadata: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    # 1.1 — optional; persisted by API when present (field names must match DB/API)
    domain: Domain | None = None
    representation: Representation | None = None
    source_tool: str | None = None
    source_format: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    source_assets: list[SourceAsset] = Field(default_factory=list)
