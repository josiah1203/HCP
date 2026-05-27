from __future__ import annotations


def kicad_pcb_with_footprints(count: int) -> bytes:
    """Build a minimal valid kicad_pcb with `count` footprints (for perf tests)."""
    header = """(kicad_pcb (version 20240108) (generator "pcbnew")
  (layers
    (0 "F.Cu" signal)
    (31 "B.Cu" signal)
    (44 "Edge.Cuts" user)
  )
  (net 0 "")
  (gr_rect (start 0 0) (end 100 100) (layer "Edge.Cuts") (width 0.1))
"""
    footprints: list[str] = []
    for i in range(count):
        ref = f"R{i + 1}"
        footprints.append(
            f"""  (footprint "R_0402" (layer "F.Cu")
    (property "Reference" "{ref}" (at 0 0 0) (layer "F.SilkS"))
    (property "Value" "10k" (at 0 0 0) (layer "F.Fab"))
  )"""
        )
    return (header + "\n".join(footprints) + "\n)\n").encode("utf-8")
