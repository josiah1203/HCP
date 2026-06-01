from __future__ import annotations

import sys
from pathlib import Path

_SDK = Path(__file__).resolve().parents[2] / "sdk" / "python"
if str(_SDK) not in sys.path:
    sys.path.insert(0, str(_SDK))
