"""pytest 共通設定。

src レイアウト + editable install 前の段階でも tests を回せるように、
src/ を sys.path に追加する。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
