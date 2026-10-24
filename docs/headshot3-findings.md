# Headshot 3 自動化 調査結果

最終更新: 2026-07-20
対象環境: Character Creator **v5.11.1823** / Headshot Plug-in **v3.1 (3.1.0623.1)** / Windows

この文書は、写真から CC5 キャラを自動生成し UE5 へ持ち込むパイプラインを構築する過程で、
**実機で確認した事実**をまとめたもの。推測は「未確認」と明記している。

---

## 1. 結論から: 使ってはいけない API と使うべき API

| API | 判定 | 根拠 |
|---|---|---|
| `RLPy.RHeadshot.CreateHeadFromPhoto` | ❌ **使用禁止** | 正しい引数でも CC5 がクラッシュする(下記 §2) |
| `RLPy2.Headshot3.GetInterface()` | ✅ 本命 | Reallusion 自身の同梱スクリプトが使う正規経路 |

`RLPy.RHeadshot` は公開メンバが `CreateHeadFromPhoto` / `ImportHeadFromObj` の2つだけで、
Headshot 3 の機能をほぼ持たない。古い API か、CC5 では機能しない残骸と推測される(未確認)。

---

## 2. `RLPy.RHeadshot.CreateHeadFromPhoto` は CC5 を落とす

### シグネチャ(判明済み)

```python
CreateHeadFromPhoto(strPhotoPath: wstring, eMode: EHSMode, kOption: RHeadshotOption)
```
`docs/rlpy-api-reference.md` L5200 に記載あり。実機の TypeError メッセージとも一致。

### クラッシュ実測(2026-07-20)

**ケース1: 不正引数**
```
CreateHeadFromPhoto(None, None, None)
  → ValueError: invalid null reference in method 'RHeadshot_CreateHeadFromPhoto',
    argument 1 of type 'std::wstring const &'
  → Python 側では例外として捕捉され、正常に見えた
  → その後 13:54:27 に CharacterCreator.exe が 0xc0000005 で終了
```

**ケース2: 完全に正しい引数**
```
CreateHeadFromPhoto(
    実在する 1254x1254 24bpp PNG,
    RLPy.EHSMode_Pro,              # attribute 経由。生 int 不使用
    RLPy.RHeadshotOption()          # 既定値
)
  → 約 15.4 秒後に transport connection 切断
  → 14:15:25 に CharacterCreator.exe が 0xc0000005 で終了
```

いずれも Windows イベントログ (Application, ID:1000) で確認。

**→ 引数の問題ではない。この API 自体がこの環境では機能しない。**

### 派生する教訓

- **SWIG ラッパに不正な引数を渡して TypeError の文面からシグネチャを推測する手法は危険。**
  Python 側で例外として返ってきても、C++ 側に不正状態が残り後からプロセスごと落ちる。
- とくに `RLPy.RFileIO.ExportFbxFile()` を引数0個で呼ぶと**即座に**CC5 が死ぬ
  (`cc5_api.py` に既存のコメントあり)。
- シグネチャ調査は次の順で行う:
  1. `docs/rlpy-api-reference.md` を検索(今回 `CreateHeadFromPhoto` は L5200 に既にあった)
  2. `Bin64/OpenPlugin/HeadShot3Kit/scripts/` の実サンプルを読む
  3. Reallusion 公式 Python API ドキュメント
  4. それでも不明ならユーザーに確認する。**推測で呼ばない**

---

## 3. 列挙値(実機取得済み)

```python
RLPy.EHSMode_Pro       = 0     # 細かく作り込むモード
RLPy.EHSMode_Auto      = 1

RLPy.EHSBodyType_Male    = 0
RLPy.EHSBodyType_Female  = 1
RLPy.EHSBodyType_Baby    = 2
RLPy.EHSBodyType_Neutral = 3
RLPy.EHSBodyType_Current = 4

RLPy.EHSLevel_Zero = 0 / _One = 1 / _Two = 2
```

### `RLPy.RHeadshotOption()` の既定値

```python
bBaby         = False
eBodyType     = 3          # Neutral
strBread      = 'None'     # ※'strBeard' の綴り誤り。原文ママで書くこと
strEyelidMask = 'None'
strFaceMask   = 'No Mask'
strMouthMask  = 'None'
strNeckMask   = 'None'
strScalp      = 'None'
strSkin       = 'Soft Skin'
```

**重要: これらは「テクスチャ/マスクのプリセット名」であり、顔の形状を指定するものではない。**
「鼻をこの形に」といった造形指定はここではできない。

---

## 4. `RLPy2.Headshot3` — 本命の経路

### 実在確認済み(Phase 1 実測)

```python
import RLPy2
hs = RLPy2.Headshot3.GetInterface()
```

### 公開メソッド 25 個

| 分類 | メソッド |
|---|---|
| 生成 | `CenerateCharacter`, `CenerateCharacterBody` |
| ランドマーク/造形 | `GetLandmarks`, `RefineMesh`, `PresetMorphSlider` |
| 画像マッチング | `ActiveImageMatching`, `DeActiveImageMatching`, `ReprojectPhoto` |
| AI 画像生成 | `AiGenFrontImage`, `AiGenSideImage`, `AiGenBodyImage` |
| スキン/テクスチャ | `GenerateSkinPhotos`, `BlendSkinPhotoDiffuse`, `BlendSkinPhotoNormal`, `GetTextureSize`, `SetTextureSize`, `RestoreTextureSetting` |
| 色 | `GetSkinColor`, `SetSkinColor`, `ResetSkinColor`, `GetEyeColor`, `SetEyeColor` |
| その他 | `SetHeadScale`, `SetIrisUVRadius`, `CheckPresetSettingsValid` |

※ `Cenerate` は Reallusion 側の綴り誤り。原文ママ。

### 呼び出し形(同梱サンプルから確定)

```python
hs.CenerateCharacter(image_file, body_type, baby,
                     face_feature_preset, skin_list, mask_list)
# BatchGenHead.py の実引数:
#   成人: Neutral, False, 空の face_feature_preset,
#         skin 3要素(先頭 'Soft Skin'), mask 4要素(先頭 'No Mask')
#   Baby: Baby, True

hs.GetLandmarks(True)    # 正面
hs.GetLandmarks(False)   # 側面
hs.RefineMesh(FrontLandmarks, SideLandmarks, enable_parts_cpp)
#   enable_parts_cpp は7要素の bool
#   index 5 = 側面フィット (RunStage2.py に "Dont Fit SideView" のコメント)
#   他6要素の意味は未確認
```

### 未確認事項

- `PresetMorphSlider` のシグネチャ。GUI の58顔プリセット + 強度スライダーに対応する可能性
- `face_feature_preset` に渡せる有効な文字列一覧(公式サンプルは常に空配列)
- `CheckPresetSettingsValid` の戻り値の意味。**生成前の事前検証に使える可能性があるので先に試す価値あり**
- `BlendSkinPhotoDiffuse` / `BlendSkinPhotoNormal` / `GenerateSkinPhotos` / `ReprojectPhoto` /
  `RestoreTextureSetting` のシグネチャと、GUI の De-Light / Redness / Primary-Secondary Normal との対応

---

## 5. Reallusion 同梱の開発スクリプト

`C:\Program Files\Reallusion\Character Creator 5\Bin64\OpenPlugin\HeadShot3Kit\scripts\`

| ファイル | 内容 |
|---|---|
| `BatchGenHead.py` | 成人の生成。引数の作り方の正解 |
| `BatchGenHeadforBaby.py` | Baby 用 |
| `ExportLandMark.py` | ランドマーク書き出し |
| `RunStage2.py` / `RunStage2Full.py` | `RefineMesh` の使い方 |
| `manual_run.py` | CC5/RLPy を使わず ONNX + MediaPipe で画像ランドマーク抽出のみ |

### ⚠️ そのままでは動かない

- ONNX モデルパスを `scripts\rtmpose-ort\...` で組むが**実体は一階層上**の
  `HeadShot3Kit\rtmpose-ort\...` にある。画像前処理部分は例外で落ちる
- `LoadFile()` が、配布元の開発機にしかないパスを読む。ローカルには存在しない

**再利用できるのは `CenerateCharacter` の呼び出し形と RLPy の保存/レンダ部分のみ。**

---

## 6. 細部造形は CC5 標準 Shaping モーフで行う

Headshot のオプションでは形状を指定できないため、生成後に Shaping モーフで追い込む。
`cc5_api.py` で実運用中の経路(実績あり):

```python
comp = avatar.GetAvatarShapingComponent()
comp.GetShapingMorphCatergoryNames()      # ※"Catergory" は Reallusion の綴り誤り
comp.GetShapingMorphIDs(category)
comp.GetShapingMorphDisplayNames(category)
comp.GetShapingMorphWeight(morph_id)
comp.SetShapingMorphWeight(morph_id, value)
```

**注意: カタログは `avatar.GetID()` をキーにキャッシュされる。
アバターが差し替わったら `_invalidate_caches()` を必ず呼ぶこと。**
呼ばないと `SetShapingMorphWeight` が黙って効かない。

`_invalidate_caches()` は `cc5_api.py` のモジュール private。
`exec_python` から `try: _invalidate_caches() except NameError: pass` と書いても
**黙って何もしない**ので、頭部生成は `cc5_api.py` 内の関数として実装すること。

---

## 7. GUI 必須と思われる機能(API 未確認)

| 機能 | 状態 |
|---|---|
| Refine Face のスプライン手動ドラッグ | GUI のみ(ただし `GetLandmarks`/`RefineMesh` で数値経由なら到達しうる) |
| 3D Sculpt Morph ブラシ | GUI のみ |
| v3.1 のペイント系(Clone/Stencil/Seamless ブラシ、Blend Mask) | GUI のみ |
| テクスチャ調整(De-Light / Skin Redness / Normal 領域別) | API 未確認。`RLPy2.Headshot3` に候補メソッドあり |

**回避策**: GUI で理想設定を一度作り `.ccAvatar` 保存 → 以後 `RLPy.RFileIO.LoadFile` で流用。

---

## 8. UE5 向け FBX 書き出し

**生 API を手書きせず、既存の `export_fbx` ツール(`target_tool="UE5"`)を使うこと。**
公式ドキュメントを見て自分でフラグを組み直すと、過去の実クラッシュから学んだ設定を落として再発させる。

### UE5 プリセットが立てるフラグ(実測)

```
flags : AutoSkinRigidMesh, ExportRootMotion, RemoveAllUnused, TPoseOnMotionFirstFrame,
        ExportPbrTextureAsImageInFormatDirectory(10-25 追加)
flags2: UnrealPreset, UnrealEngine4BoneAxis, YUp, ResetSkinPose, ResetBoneScale
flags3: ExportJson
```

### なぜ必要か(2026-07-02 の実測記録)

- `ExportPbrTextureAsImageInFormatDirectory` が無いと、肌のつや・透け・細かい凹凸・表情のしわ、髪の根元・流れの画像が
  書き出されず(json のパスが空)、UE の肌がのっぺり見える(10-25、v58b/v59/Ariana で確認)。
  あわせて UE5 プリセットは `texture_size` 未指定なら元の大きさ(`EExportTextureSize_Original`)で書き出す
  (指定しないと 2048 に縮んでいた)。`SetTextureSize` は画素数ではなく `EExportTextureSize_*` を受け取る。


- `EExportFbxOptions3_ExportJson` が無いと、UE の `UCCFbxFactory` が
  `Array index out of bounds` でクラッシュする
- `EExportFbxOptions2_ResetSkinPose` / `_ResetBoneScale` が無いと bind-pose 行列が不一致になり、
  UE が T0-as-ref-pose を強制して morph インポートが決定的にクラッシュする
  (無しで 11/14 メッシュ不正、有りで 14/14 が 1e-6 で有効)

### 既知の文書不備

`src/tools/asset.ts` と `CLAUDE.md` のツール説明が `embed_textures=true` を推奨しているが、
**Auto Setup 公式は Embed Textures = OFF が正しい**(JSON + 外部テクスチャフォルダを Auto Setup が読むため)。
実装のデフォルトは `False` なので実害は説明文のみ。**説明文を修正すべき。**

---

## 9. 開発運用上の落とし穴

### 9-1. リポジトリ版と稼働版は別ファイル

CC5 がロードしているのは **Program Files 配下**のプラグイン。
リポジトリの `cc5-plugin/cc5_api.py` を編集しても**そのままでは反映されない**。

```
1. cc5-plugin/cc5_api.py を編集
2. scripts/copy_to_installed.ps1 で配備
3. 双方の SHA-256 一致を確認
4. GET http://127.0.0.1:5101/reload
5. CC5 内で hasattr(cc5_api, '新関数名') == True を確認
```

これを飛ばすと HTTP 400(関数が見つからない)になる。

### 9-2. ホットリロードの実際の範囲

`reload_modules()`(server.py)は `cc5_api` を再読込する。再読込のときに
`cc5_api.py` の末尾の `_auto_patch_server()` が走り、そこに書かれた分だけ
server の `ACTION_MAP` / `POST_ROUTES` / `GET_ROUTES` / `REQUIRED_PARAMS` を更新する。
(補足 2026-10-19: 当初この節は「`_auto_patch_server()` は存在しない」と書いていたが、
これは server.py を探したための誤り。関数は cc5_api.py にある。)

| 変更対象 | `/reload` で反映されるか |
|---|---|
| `cc5_api.py` の既存関数の中身 | ✅ される |
| `cc5_api.py` への新関数・新 route の追加 | ✅ `_auto_patch_server()` の表にも足した場合だけ |
| `main.py` / `server.py` の変更 | ❌ 再起動/プラグイン再ロードが必要 |
| server.py だけに足した route | ❌ 同上 |

なお 1.2.0 からは、`/reload` は `CC5_DEV_MODE=1`(または `CC5_RELOAD_SECRET`)のときだけ使える。

### 9-3. モーダルダイアログで全処理が止まる

CC5 プラグインのコマンドキューは **QTimer でメインスレッド上**を回る。
モーダルダイアログが出ている間は `exec_python` が実行されない。
**ブリッジは「接続済み」に見えるのに処理が進まない**という状態になる。

実際に発生した例(CC5 クラッシュ後の再起動時):
```
「Unsaved project data found. Would you like to update your project
  with the unsaved changes?」 [OK] [Cancel]
```

対策として、手元で監視用の PowerShell スクリプトを用意した(このリポジトリには含まない)。
CC5 の可視ウィンドウを列挙してメインウィンドウ以外をダイアログとして検知し、
スクリーンショットを自動保存する。ブリッジ疎通の変化も通知する。

**注意: このスクリプトは PowerShell 7 (`pwsh`) で実行すること。**
`powershell.exe` (5.1) は BOM なし UTF-8 の日本語を ANSI として読むため構文エラーになる。

### 9-4. 検証は数値だけでなく目視でも行う

`capture_viewport` でスクリーンショットを撮り、結果を目で確認すること。
ログや戻り値だけで「できた」と判断しない。頭部生成後はとくに必須。

---

## 10. 未解決の課題

1. `RLPy2.Headshot3.CenerateCharacter` 経路での生成が成功するか(次の検証対象)
2. `PresetMorphSlider` で「鼻/口の形」を指定できるか
3. `face_feature_preset` の有効な文字列一覧
4. テクスチャ調整系メソッドのシグネチャ
5. `CheckExportFbxHasLicense` / `IsCompatibleWithExportOption` の戻り値の意味
