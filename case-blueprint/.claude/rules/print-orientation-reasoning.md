# print_orientation 推論ルール — どの面を bed に接地させるか

`case-spec.yaml` の `case.print_orientation.body` / `lid` を決める判断ルール。
`/design` SKILL.md が初回の自動判断、`/review-fix` SKILL.md が利用者からの修正反映で参照する。
落とし穴は `pitfalls.md` P1 / P2。

## 印刷向きの「向きの軸」

各パーツについて「どの面が bed 接地面か」を 1 つ選ぶ。表記は軸記法または通称:

- `+Z bottom` (= `bottom_down` の通称) — `+Z` 面が下、つまり標準的な向き
- `-Z bottom` (= `top_down`) — `-Z` 面が下、上下逆さ
- `+Y bottom` (= `back_down`) / `-Y bottom` (= `front_down`)
- `+X bottom` / `-X bottom`

generator.py 出力時点では canonical orientation で出し、print 時に rotate を効かせる。
`output/print/*.3mf` には印刷向きを焼き込む(`/export` SKILL.md 参照)。

## 判断の優先順位

以下を上から順に評価し、合致した時点で確定する。後の規則ほど例外的状況。

### 1. 細部・最終層に出したい面を **上**(終層)に向ける(P1)

- 文字 emboss / 装飾フィレット / 細い壁(< 1.5mm)
- 蓋なら標準的に `top_down`(蓋表面 = 印刷終盤、底面 = 接着面)
- 本体なら `bottom_down`(底面 = 接着面、開口部 = 終盤、リップ受けが綺麗に出る)

### 2. オーバーハングを最小化する(P2)

- 50° 超のオーバーハング部位はサポート必須
- ケースで頻発する難所:
  - **蝶番ナックルの上半分** — ブリッジングで対応可(短い PLA なら問題なし)
  - **カラビナタブの根元** — 配置によりサポートが必要
  - **張り出し・庇** — 真上に向ける配置を避ける
- ツリー/オーガニックサポート対応プリンタなら自由度が上がる

### 3. コネクタ・ボタンのある面を bed に接しさせない

- `object.connectors[].face` / `object.controls[].face` が指定されていれば、それらと同じ face を本体の `bottom` にしない
- USB ポートが面ごと bed 接地 → 印刷後の vase line 跡で port が変形しがち
- 例: connectors が `+X` にあるなら `print_orientation.body: -Z bottom` か `+Y bottom`(コネクタ面が垂直に立つ向き)

### 4. 強度が必要な軸を **層方向と直交させる**

- 衝撃や曲げ荷重がかかる方向は、層間接着が **その方向の張力に耐える** 向きが望ましい
- 一般則: 「割れたら困る方向」が **印刷の積層方向と直交** するようにする
- 例: 蓋ヒンジ部の引っ張り荷重が Y 方向 → 印刷時の Z 軸を Y にしない(蝶番が層剥離で割れる)

### 5. bed 接地面積を確保する(反り対策)

- 大きな平面が bed に接するほど安定
- 接地面が狭すぎる(< 30 × 30 mm 程度)とブリム/ラフトが必要
- 蓋を `top_down` にすると蓋の天面全体が接地で安定

### 6. 印刷時間と材料の収縮を考慮(ABS/PETG)

- 反りやすい材料(ABS, PETG)は接地面を**広く・長辺を bed 短辺と平行に**
- `data/materials/<id>.yaml` の `shrinkage.linear_pct` が高い材料(0.6% 超)はこの考慮が効く

## 既定値(L0 の自動判定)

`object.orientation_hint` が指定されていない場合、Claude は以下の既定で進める:

| パーツ | 既定 | 理由 |
|---|---|---|
| body | `+Z bottom` (`bottom_down`) | 底接地、開口部が終盤、リップ受けが鮮明 |
| lid | `-Z bottom` (`top_down`) | 蓋天面接地、内側のリップ・装飾が終盤で出やすい |
| latch-lever (hinge_lever) | `-Z bottom`(平面接地) | 平らな面で接地、ピン穴が垂直 |

## オブジェクトの `orientation_hint` を尊重する

`object.yaml` の `orientation_hint` が指定されている場合、それを優先する:

```yaml
orientation_hint:
  bottom_preference: "+Z"          # ボトムが +Z 側に向く設計優先
  top_preference: "-Z"             # トップを -Z 側にしたい(細部が来る)
  forbidden_bottoms: ["+X", "-X"]  # コネクタ面のため、X 面は底に置けない
```

このヒントは object 単体の話ではなく、**object をケース内に組んだ時の世界座標**で
解釈される(case-spec の position / rotation 適用後)。

## レビュー観点(`/fit-check` 経由で点検)

- `print_orientation` が `connectors[].face` / `controls[].face` と矛盾していないか
- `forbidden_bottoms` が守られているか
- ヒンジ蓋ケースで蓋ナックル列の Z 方向(層方向)が荷重方向と直交しているか

矛盾を検出したら ⚠ で警告し、`/review-fix` で利用者と相談する。

## 関連

- `@.claude/skills/design/SKILL.md` — 初回の print_orientation 設定
- `@.claude/skills/review-fix/SKILL.md` — 修正時の見直し
- `@.claude/skills/export/SKILL.md` — slicer-notes に向き根拠を記載
- `@.claude/rules/materials-catalog.md` — 反りやすい材料の特性
- `@.claude/pitfalls.md` — P1(向きミス)、P2(オーバーハング)
- `@schemas/object.schema.yaml` — `orientation_hint` / `connectors` / `controls`
