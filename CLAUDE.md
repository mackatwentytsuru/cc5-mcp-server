# CC5 MCP Server — Project Context

## 概要
Reallusion Character Creator 5 (CC5) を Claude などの LLM から自然言語で操作するための MCP サーバー。

## アーキテクチャ

```
LLM (Claude) <--stdio--> MCP Server (Node.js) <--HTTP:5100--> CC5 Plugin (Python/Flask-free) <--RLPy--> CC5
```

## ディレクトリ構成

```
cc5-mcp-server/
├── src/                    # MCP Server (TypeScript)
│   ├── index.ts            # エントリポイント
│   ├── cc5-bridge.ts       # CC5 HTTP クライアント
│   ├── types.ts            # 型定義
│   ├── tools/              # MCP ツール定義
│   │   ├── morph.ts        # モーフ調整ツール
│   │   ├── scene.ts        # シーン管理ツール
│   │   ├── asset.ts        # アセット読込/FBX書出
│   │   └── character.ts    # 高レベルキャラ操作
│   └── resources/
│       └── morphs.ts       # モーフカタログリソース
├── cc5-plugin/             # CC5 Python プラグイン
│   ├── main.py             # CC5 プラグインエントリ (load_plugin/unload_plugin)
│   ├── server.py           # Python 標準 http.server ブリッジ
│   ├── cc5_api.py          # RLPy API ラッパー
│   ├── config.json         # CC5 プラグイン設定
│   └── config.xml          # CC5 プラグイン設定 (XML フォーマット)
├── start_bridge.py         # CC5 Script Editor から手動起動用
├── install-plugin.ps1      # プラグインインストールスクリプト (要管理者権限)
├── claude-mcp-config.json  # Claude Code 用 MCP 設定スニペット
└── CLAUDE.md               # このファイル
```

## 重要な技術情報

- **CC5 Python バージョン**: Python 3.10
- **CC5 Qt バインディング**: PySide2 (PySide6 ではない！)
- **RLPy スレッド安全性**: NOT スレッドセーフ — 全 RLPy 呼び出しは QTimer 経由でメインスレッドで実行
- **ブリッジ方式**: Flask 不使用、Python 標準 `http.server` を使用
- **ブリッジポート**: 5100 (環境変数 CC5_BRIDGE_URL で変更可)

## セットアップ手順

### 1. MCP Server ビルド
```bash
cd cc5-mcp-server
npm install
npm run build
```

### 2. CC5 プラグインインストール (管理者権限必要)
```powershell
# 管理者 PowerShell で実行
powershell -Command "Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass -File C:\Users\macka\Projects\cc5-mcp-server\install-plugin.ps1' -Verb RunAs"
```

### 3. Claude Code への MCP 登録
~/.claude.json の mcpServers に以下を追加済み:
```json
"cc5": {
  "command": "node",
  "args": ["C:/Users/macka/Projects/cc5-mcp-server/build/index.js"],
  "env": { "CC5_BRIDGE_URL": "http://127.0.0.1:5100" }
}
```

### 4. CC5 ブリッジ起動

**方法A: プラグイン自動起動（推奨）**
CC5 を起動すると OpenPlugin/CC5_MCP_Bridge/ が自動的にロードされる。
CC5 の Plugin Manager で有効化が必要な場合がある。

**方法B: Script Editor から手動起動**
CC5 メニュー → Script → Load Python → `start_bridge.py` を選択して実行

## 利用可能な MCP ツール (11個)

| ツール | 説明 |
|--------|------|
| check_cc5_connection | CC5 接続確認 |
| list_avatars | シーン内アバター一覧 |
| get_avatar_info | アバター詳細情報・モーフ値 |
| describe_character | 自然言語でキャラ外見を記述 |
| adjust_morph | 単一モーフスライダー調整 |
| adjust_multiple_morphs | 複数モーフ一括調整 |
| get_morph_value | モーフ現在値取得 |
| apply_body_preset | 体型プリセット適用 |
| set_subdivision_level | HD 細分化レベル設定 |
| load_asset | アセットファイル読込 |
| export_fbx | FBX エクスポート |

## 開発メモ

- ビルド: `npm run build`
- 開発中ウォッチ: `npm run dev`
- CC5 プラグイン更新後は CC5 再起動が必要
- ポート変更: cc5-plugin/main.py の `BRIDGE_PORT` を変更して再インストール
