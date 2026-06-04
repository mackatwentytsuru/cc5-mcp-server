# CC5 MCP Server — Development Rules

## Bridge Operations

- CC5 起動時にブリッジは自動起動する (port 5101, 約7-10秒)
- ブリッジの生死確認: `curl -s http://127.0.0.1:5101/health`
- cc5_api.py を変更したら: `curl http://127.0.0.1:5101/reload` で即反映
- server.py を変更したら: CC5 再起動が必要

## CC5 再起動時の重要事項

CC5 を再起動するときは必ず以下の順序:
1. `taskkill //F //PID <pid>` で終了
2. `CharacterCreator.exe &` で起動
3. ブリッジ起動を待機 (health check ポーリング)
4. **ダイアログを自動クローズ** — CC5 は起動時にダイアログを表示する:
   - 「Unsaved project data found」→ `SendKeys('{ENTER}')` で OK
   - ウェルカム画面 → `SendKeys('{ESCAPE}')` で閉じる
   - **これらを閉じないとビューポートが正しくレンダリングされない**
5. 恒久対策: ユーザーに「Don't show this again」をチェックしてもらう

## ビューポートキャプチャ

`capture_viewport` は RenderImage → ForceViewportUpdate+リトライ → Windows スクリーンショットの3段階フォールバック。
.ccProject 読み込み後は RenderImage が動かないことがあるため、フォールバックが重要。

## コード変更のワークフロー

1. cc5_api.py に Python 関数を追加/修正
2. `_auto_patch_server()` に新アクションを追加（ACTION_MAP + routes）
3. server.py に ACTION_MAP / POST_ROUTES / REQUIRED_PARAMS を追加
4. `curl http://127.0.0.1:5101/reload` でリロード
5. `curl` で実機テスト
6. TypeScript 側 (types.ts → cc5-bridge.ts → tools/*.ts → index.ts) を追加
7. `npm run build` でビルド確認
8. `npm test` でテスト確認

## RLPy API 参照

- 完全なAPI リファレンス: `docs/rlpy-api-reference.md` (5,393行)
- 163クラス、90 Enum グループ、287グローバル関数
- 新機能追加時はまずこのファイルで API の存在を確認

## RLPy の制約

- RLPy は NOT スレッドセーフ — QTimer 経由でメインスレッドからのみ呼び出し可能
- SWIG バインディング — 無効な引数で C++ セグフォルトの可能性あり
- 必ず引数を事前検証してから RLPy を呼び出す
- `BeginAction()` / `EndAction()` — 変更操作は必ず囲む。try/finally で EndAction を保証
- `ObjectModified()` — 変更後に必ず呼び出す（ビューポート更新に必要）

## プラグインの仕組み

- エントリポイント: `initialize_plugin()` / `uninitialize_plugin()` (load/unload は不可)
- プラグイン情報: `rl_plugin_info = {"ap": "iClone", "ap_version": "8.0"}`
- CC5 は iClone 8 エンジンベース — `"Character Creator"` や `"4.0"` は認識されない
- PySide2 必須（PySide6 不可）
- `from __future__ import annotations` 必須（Python 3.10 型ヒント互換性）

## テスト

- ユニットテスト: `npm test` (314件)
- カバレッジ: `npm run test:coverage` (80%+ 閾値)
- 実機テスト: `curl` でブリッジに直接リクエスト
- API ディスカバリ: `curl http://127.0.0.1:5101/api`
