"""case_blueprint — 3D プリント可能ケース設計ハーネスの共通実装。

提供:
  - loader:           YAML 読み込み + JSON-Schema 検証
  - geometry:         内寸/外寸/配置計算
  - exporter:         STEP/STL/3MF エクスポート
  - feature_registry: features dispatcher の基盤
  - validators:       @check decorator による検証ベース
  - state:            /lead 用の現在地スナップショット (JSON)
  - closures:         closure.method 別実装(hinge_lever 等)
"""

__version__ = "0.1.0"
