# CC5 MCP Server — Project Context

## 概要
Reallusion Character Creator 5 (CC5) を Claude などの LLM から自然言語で操作するための MCP サーバー。

## アーキテクチャ

```
LLM (Claude) <--stdio--> MCP Server (Node.js) <--HTTP:5101--> CC5 Plugin (Python) <--RLPy--> CC5
```

## 起動の仕組み（重要）

### 自動起動フロー（通常の動作）

```
CC5 起動
  → OpenPlugin/CC5_MCP_Bridge/main.py を自動検出
  → rl_plugin_info をチェック（CC5 互換性確認）
  → initialize_plugin() を呼び出し
    → bridge_server.start_server(port=5101) で HTTP サーバー起動
    → QTimer(16ms) で process_command_queue を登録
  → ブリッジが http://127.0.0.1:5101 で待機開始
```

**自動起動に必要な3つの条件:**
1. `main.py` に `initialize_plugin()` 関数（CC5 の命名規約。`load_plugin` は不可）
2. `main.py` に `rl_plugin_info = {"ap": "iClone", "ap_version": "8.0"}` 辞書（CC5 は iClone 8 エンジン）
3. プラグインが `OpenPlugin/CC5_MCP_Bridge/` にインストール済み

**よくある問題と対処:**
- `load_plugin` → CC5 は無視する。必ず `initialize_plugin` を使う
- `PySide6` → CC5 は PySide2。インポートエラーでサイレント失敗
- `from __future__ import annotations` がない → Python 3.10 で型ヒントエラー
- Flask 依存 → CC5 の Python に Flask はない。stdlib `http.server` を使う

### ウォッチドッグ（自動復旧）

QTimer コールバックにサーバーヘルスチェックを内蔵:
```python
def _check_server_health():
    if _server_thread is not None and not _server_thread.is_alive():
        _server_thread = bridge_server.start_server(port=BRIDGE_PORT)
```
→ HTTP サーバースレッドがクラッシュしても、次の QTimer tick で自動再起動

### ホットリロード（コード変更の即時反映）

```
cc5_api.py を編集
  → curl http://127.0.0.1:5101/reload (または Claude が自動実行)
  → importlib.reload(cc5_api) が実行される
  → _auto_patch_server() が ACTION_MAP / POST_ROUTES / GET_ROUTES を更新
  → 新しいコードが即座に有効化（CC5 再起動不要）
```

**制限:** server.py の変更（ルート追加、バリデーション変更等）は CC5 再起動が必要。
cc5_api.py の変更（API 関数の修正、新関数追加）はリロードで即反映。

### トラブルシューティング

| 症状 | 原因 | 対処 |
|------|------|------|
| CC5 起動してもブリッジが立たない | `initialize_plugin` でない / `rl_plugin_info` がない | main.py の関数名・辞書を確認 |
| ポート 5101 に接続できない | プラグイン未インストール | `install-plugin.ps1` を管理者権限で実行 |
| `curl /reload` が 404 | 古い server.py が動いている | CC5 を再起動して新しい server.py を読み込み |
| RLPy の関数が見つからない | CC5 バージョン差異 | `hasattr()` でチェックしてグレースフルに失敗 |
| モーフが効かない | アバターがシーンにいない | `create_avatar` で先にアバターを作成 |
| マテリアル色が変わらない | メッシュ/マテリアル名が間違い | `get_material_info` で正しい名前を確認 |
| Undo が効かない | `BeginAction/EndAction` で囲まれていない | 変更操作は必ず BeginAction/EndAction で囲む |
| キャプチャが空画像 | シーンにアバターがいない | アバター作成 → モーフ適用 → キャプチャ |
| RenderImage が失敗 | .ccProject 読み込み後に発生することがある | 自動で Windows スクリーンショットにフォールバック |
| ウェルカムダイアログが邪魔 | CC5 起動時に表示される | `scripts/cc5-restart.ps1` で自動 Close、または「Don't show this again」にチェック |
| FBX エクスポートがライセンスエラー | キャラに iContent ライセンスのアセットが含まれている | Help→Activate Purchased Items を試す。Content Store アセットを外せばデフォルトコンテンツはエクスポート可。アップグレードは定価の20% |
| カメラ焦点距離が変わらない | Preview Camera は API で変更不可 | CC5 で新規カメラを作成して使用。API は正直にエラーを返す |
| 色の範囲 | 入力は 0.0-1.0、RLPy は 0-255 を返す | API 側で正規化済み（0.0-1.0 で統一） |
| `set_subdivision_level` で HD ディテールが増えない / `max_level` が 0 を返す | SubD（HD サブディビジョン）データの生成は CC5 UI 専用の `Modify > Subdivide` 操作。RLPy からは生成できない。アバターに HD データが未生成だと `max_level = 0` になる | これは失敗ではなく仕様。HD を使うには CC5 UI で一度 `Modify > Subdivide` を実行して HD データを生成しておく。生成済みなら API でレベル切替が効く |
| CC5 5.07 未満で SubD/HD やプラグインの挙動がおかしい | 5.07 より前のビルドは SubD キャッシュやプラグインモジュールの再構築が必要なことがある | CC5 を 5.07 以降に更新する。更新できない場合はプロジェクトを開き直して SubD を再生成（rebuild）してから API 操作を行う |

### サブディビジョン（SubD / HD）についての補足

`set_subdivision_level` はあくまで「既に生成済みの HD サブディビジョンレベルを切り替える」ツール。
HD データそのものの**生成**は CC5 の UI 操作 `Modify > Subdivide` でのみ可能で、RLPy/API からはトリガーできない。
そのため、HD 未生成のアバターでは `max_level = 0`（HD データなし）となり、これは**エラーではなく正常な状態**。
`export_fbx` の `sub_d_level` も同様で、HD データが無いアバターでは高レベルを指定しても効果がない。

> **5.07 未満の注意:** CC5 5.07 より前のビルドでは、SubD キャッシュ／プラグインモジュールの再構築（rebuild）が必要になるケースがある。可能なら 5.07 以降へ更新する。

### export_fbx の詳細

`export_fbx` は CC5「Export FBX (InstaLOD)」ダイアログを `RLPy.RExportFbxSetting` で再現する。
全パラメータは任意（`output_path` のみ必須）で、既存の挙動と完全な後方互換を保つ。

| パラメータ | ダイアログ項目 | 説明 |
|-----------|--------------|------|
| `output_path` | 出力先 | ディレクトリ無しのファイル名（例 `character.fbx`）は `D:\CC5Export` 配下に解決される（`CC5_EXPORT_DIR` で変更可）。絶対パスはそのまま使用。 |
| `target_tool` | Target Tool Preset | `"UE5"`/`"Unreal"` で Unreal 向けフラグ（Y-up, UE bone axis）を適用。 |
| `export_motion` | FBX Options | `true` = "Mesh and Motion"（既定）、`false` = "Mesh" のみ。`EnableExportMotion` を使用。 |
| `sub_d_level` | HD Character Subdivision Level | 0/1/2。`SetExportLevel`（シーンを変更しない）で適用。2-arg フォールバック時のみ `set_subdivision_level` を使用。 |
| `embed_textures` | Texture Settings: Embed Textures | `EExportFbxOptions_EmbedTexture` を付与。 |
| `convert_image_format` | Texture Settings: Convert Image Format | `EExportFbxOptions_ConvertTifToPNG` を付与。 |
| `texture_size` | Texture Settings: Max Texture Size | `SetTextureSize`（0 = 元サイズ）。 |
| `fps` | Include Motion: Frame Rate | `RLPy.RFps.Fps{n}`（例 30）にマップ。未対応値は note を付けてスキップ。 |
| `motion_range` | Include Motion: 範囲 | `[start, end]` を `SetExportMotionRange` に渡す。省略時は既定の "All"。 |

**推奨 Unreal (UE5 Skeleton) 呼び出し:** `target_tool="UE5"`, `export_motion=true`, `sub_d_level=0`, `embed_textures=true`, `fps=30`（`motion_range` は省略 = All）。InstaLOD は常に OFF。

返り値は実際に適用された値のみを正直に報告する（`export_level`, `export_motion`, `fps`, `motion_range`, `texture_size`, `embed_textures` 等）。`RExportFbxSetting` が利用できない 2-arg フォールバック時は、適用できなかったオプションを `notes` に WARNING として記録する。

### CC5 再起動の完全手順（Claude が自動実行）

```bash
# 1. CC5 を正常終了（//F を使わない → 未保存ダイアログ防止）
pid=$(tasklist 2>/dev/null | grep "CharacterCreator" | awk '{print $2}')
taskkill //PID $pid
sleep 15  # 正常終了は時間がかかる。15秒待つ
# まだ生きていたら強制終了
tasklist 2>/dev/null | grep -q "CharacterCreator" && taskkill //F //PID $pid
sleep 5

# 2. CC5 を起動（プラグインが自動でブリッジを起動する）
"/c/Program Files/Reallusion/Character Creator 5/Bin64/CharacterCreator.exe" &

# 3. ブリッジの起動を待機（通常 7-10秒）
for i in $(seq 1 60); do
  curl -s --connect-timeout 1 http://127.0.0.1:5101/health | grep -q "ok" && break
  sleep 2
done

# 4. 起動時ダイアログを自動クローズ（重要！）
#   a) 「Unsaved project data found」→ Enter で OK（正常終了なら出ない）
#   b) ウェルカム画面 → Escape で閉じる（「Don't show this again」済みなら出ない）
#   これらを閉じないとビューポートが正しくレンダリングされない
sleep 5
powershell -ExecutionPolicy Bypass -File scripts/cc5-restart.ps1
```

### ダイアログの恒久対策
CC5 のウェルカム画面で「Don't show this again」にチェックを入れて Close すると、
次回以降はウェルカムダイアログが表示されなくなる。
ユーザーに一度だけこの操作をしてもらうのが最も確実。

### ビューポートキャプチャの仕組み
`capture_viewport` は3段階のフォールバックで動作:
1. **RLPy.RenderImage()** — 最速、通常はこれで成功
2. **ForceViewportUpdate + リトライ** — RenderImage 初回失敗時
3. **Windows スクリーンショット（PowerShell）** — .ccProject 読み込み後など RenderImage が完全に動かない場合

注意: フォールバック3は全画面キャプチャなので、CC5 ウィンドウが最前面にある必要がある。

## ディレクトリ構成

```
cc5-mcp-server/
├── src/                    # MCP Server (TypeScript)
│   ├── index.ts            # エントリポイント
│   ├── cc5-bridge.ts       # CC5 HTTP クライアント
│   ├── types.ts            # 型定義
│   ├── util.ts             # 共通ユーティリティ (bridgeCall)
│   ├── tools/              # MCP ツール定義 (12ファイル)
│   │   ├── morph.ts        # モーフ調整 + 検索 + リセット
│   │   ├── scene.ts        # シーン管理 + キャプチャ
│   │   ├── asset.ts        # アセット読込/FBX書出
│   │   ├── character.ts    # 体型プリセット + 外見記述
│   │   ├── content.ts      # コンテンツ管理 (衣服/髪/アクセサリー)
│   │   ├── color.ts        # 便利色設定 (目/髪/唇)
│   │   ├── visibility.ts   # 表示/非表示 + シーンオブジェクト一覧
│   │   ├── edit.ts         # Undo/Redo
│   │   ├── camera.ts       # カメラ制御
│   │   ├── light.ts        # ライト制御
│   │   ├── expression.ts   # 表情情報
│   │   └── material.ts     # マテリアル/色制御
│   └── resources/
│       └── morphs.ts       # モーフカタログリソース
├── cc5-plugin/             # CC5 Python プラグイン
│   ├── main.py             # プラグインエントリ (initialize_plugin/uninitialize_plugin)
│   ├── server.py           # HTTP ブリッジサーバー
│   ├── cc5_api.py          # RLPy API ラッパー (全API関数 + _auto_patch_server)
│   ├── config.json         # プラグイン設定
│   └── config.xml          # プラグイン設定 (XML)
├── tests/                  # テスト (314件, 12ファイル)
├── start_bridge.py         # 手動起動用（通常不要 — 自動起動が動作するため）
├── install-plugin.ps1      # プラグインインストール (要管理者権限)
├── claude-mcp-config.json  # Claude Code 用 MCP 設定
└── CLAUDE.md               # このファイル
```

## 重要な技術情報

- **CC5 Python**: Python 3.10 + PySide2（PySide6 ではない！）
- **RLPy**: NOT スレッドセーフ — QTimer 経由でメインスレッド実行必須
- **ブリッジ**: `http.server` (Flask 不使用) on port 5101
- **QTimer**: 16ms 間隔（~60fps）— レスポンス最適化済み
- **プラグイン関数名**: `initialize_plugin` / `uninitialize_plugin`（`load/unload` は不可）
- **型ヒント互換性**: `from __future__ import annotations` 必須
- **モーフ値範囲**: [-1.0, 1.0]（負の値で特徴を縮小）
- **morph ID キャッシュ**: アバター変更時に自動無効化

## セットアップ手順

### 1. MCP Server ビルド
```bash
npm install && npm run build
```

### 2. CC5 プラグインインストール (管理者権限)
```powershell
powershell -ExecutionPolicy Bypass -File install-plugin.ps1
```

### 3. Claude Code への MCP 登録
```json
"cc5": {
  "command": "node",
  "args": ["<path-to-project>/build/index.js"],
  "env": { "CC5_BRIDGE_URL": "http://127.0.0.1:5101" }
}
```

### 4. CC5 起動 → 自動でブリッジ起動（手動操作不要）

## 利用可能な MCP ツール (56個)

### シーン管理
| ツール | 説明 |
|--------|------|
| check_cc5_connection | CC5 接続確認 |
| list_avatars | シーン内アバター一覧 |
| get_avatar_info | アバター詳細情報・モーフ値 |
| create_avatar | ニュートラルCC3+素体作成 (テクスチャ無し=マネキン。実顔は browse_content("character")+load_asset 推奨) |
| delete_avatar | アバター削除 (名前指定 or 全削除。マネキン除去→実キャラ読込に使う) |
| describe_character | 自然言語でキャラ外見を記述 |
| get_scene_objects | シーン内全オブジェクト一覧 (アバター, プロップ, ライト, カメラ) |

### モーフ操作
| ツール | 説明 |
|--------|------|
| search_morphs | モーフカタログをキーワード検索 |
| adjust_morph | 単一モーフスライダー調整 [-1, 1] |
| adjust_multiple_morphs | 複数モーフ一括調整 (最大500) |
| get_morph_value | モーフ現在値取得 |
| reset_morphs | 全モーフをゼロにリセット |
| apply_body_preset | 体型プリセット (athletic/muscular/slim/heavy/average) |

### コンテンツ管理 (衣服・髪・アクセサリー)
| ツール | 説明 |
|--------|------|
| list_clothes | アバター上の衣服一覧 |
| list_hair | アバター上の髪型一覧 |
| list_accessories | アバター上のアクセサリー一覧 |
| remove_scene_item | 衣服/髪/アクセサリーを名前で削除 |
| browse_content | CC5コンテンツフォルダを参照 (衣服/靴/アクセサリー + pose/motion/expression/props/light/camera/character) |

### カメラ・ライト・表情
| ツール | 説明 |
|--------|------|
| get_camera_info | カメラ位置・焦点距離取得 |
| set_camera_focal_length | カメラ焦点距離設定 |
| frame_camera | プリセット視点 (face/front/home/all 等) にカメラを移動 |
| get_lights | シーン内ライト一覧 (重複排除済み) |
| get_light_info | ライト詳細 (色/強度/オンオフ/影キャスト/影濃度/レンジ) |
| set_light_color | ライトRGBカラー変更 |
| set_light_multiplier | ライト強度 (multiplier) 設定 |
| set_light_active | ライトのオン/オフ切替 (ライティング調整) |
| set_light_shadow | 影キャストON/OFF + 影の濃さ (darken 0-1) 設定 |
| get_visual_settings | 環境光取得 (ambient 色 + IBL 有効状態) |
| set_ambient | シーンの環境(フィル)光カラー設定 (0-1) |
| set_ibl | IBL/HDRI 有効化・無効化 + HDRI 画像ロード |
| get_expression_info | 表情グループ・スライダー名取得 |
| set_expression | 表情スライダーを名前で設定 (weight 0-1, 複数可) |
| reset_expression | 全表情スライダーを 0 (ニュートラル) にリセット |

### マテリアル・色
| ツール | 説明 |
|--------|------|
| get_material_info | メッシュ・マテリアル名一覧 |
| get_shader_parameters | Digital Human Shader パラメータ取得 (肌ラフネス/SSS/MicroNormal 等) |
| set_shader_parameter | Digital Human Shader パラメータ設定 (名前+値リスト、検証つき) |
| get_diffuse_color | ディフューズカラー取得 |
| set_diffuse_color | ディフューズカラー設定 (肌色等) |
| set_eye_color | 目の色設定 (便利ショートカット) |
| set_hair_color | 髪の色設定 (便利ショートカット) |
| set_lip_color | 唇の色設定 (便利ショートカット) |

### 表示/非表示
| ツール | 説明 |
|--------|------|
| set_item_visible | シーンアイテムの表示/非表示切替 |

### アセット・エクスポート
| ツール | 説明 |
|--------|------|
| load_asset | アセット読込 (.iAvatar, .ccAvatar, .ccm 等) |
| export_fbx | FBX エクスポート（CC5「Export FBX」ダイアログを再現）。詳細は下記「export_fbx の詳細」を参照。|
| set_subdivision_level | HD 細分化レベル |
| capture_viewport | ビューポートスクリーンショット (画像をLLMに返却) |

### ActorMIXER PRO
| ツール | 説明 |
|--------|------|
| create_actor_mixer | ネイティブ「Create Mixer Assets」ダイアログを駆動して .ccMixerPreset を生成。`confirm_create` が安全ゲート (false=フィールド設定後キャンセルするドライラン / true=Create クリック)。ActorMIXER PRO プラグインが必要 |

### 編集
| ツール | 説明 |
|--------|------|
| undo | 最後の操作を元に戻す |
| redo | 元に戻した操作を再適用 |

## 開発メモ

- ビルド: `npm run build`
- テスト: `npm test` (449件) / `npm run test:coverage`
- ホットリロード: `curl http://127.0.0.1:5101/reload` (cc5_api.py の変更を即反映)
- API ディスカバリ: `curl http://127.0.0.1:5101/api`
- CC5 再起動: `taskkill` → `CharacterCreator.exe &` → ブリッジ自動起動

## 環境変数

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| CC5_BRIDGE_URL | http://127.0.0.1:5101 | ブリッジ接続先 |
| CC5_BRIDGE_PORT | 5101 | ブリッジポート (start_bridge.py用) |
| CC5_RELOAD_SECRET | (空) | /reload 認証トークン |
| CC5_DEV_MODE | 1 | 開発モード (1=reload有効) |
| CC5_REQUEST_TIMEOUT_MS | 30000 | リクエストタイムアウト (ms) |
| CC5_ROOT | (自動検出) | CC5 インストールパス |
