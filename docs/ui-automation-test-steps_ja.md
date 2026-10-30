# UI の自動操作: 金剛の CC5 で試す手順(2026-10-26)

作った人は金剛の CC5 に一度もつないでいません。**ここに書いたことは全部「まだ実機で確かめていない」**ものです。
撮影が終わったあとに、壊れてもよいプロジェクトで、上から順に試してください。

## 足したもの(1 分で読む)

- 型・部品を当てる: `apply_preset`(まつげの型、まつげの部品、口紅などの SkinGen の型)
- 手元にある型の一覧: `list_presets`
- SkinGen: `skingen_editor`(オン・オフ、切ると焼き込みの終わりまで待つ)/ `skingen_layer`(選ぶ・表示/非表示・濃さ 0〜100・消す)/ `skingen_state`(読むだけ)
- 窓に気づく: `list_cc5_windows`(CC5 の中の Qt で題名・文章・ボタンを読み、絵(PNG)も撮る。読むだけ)/ `get_ui_job`(続きを見る)/ `find_ui_widgets`(部品の名前を探す。読むだけ)
- 撮影: `capture_framed_crop`(顔を枠に入れて大きく撮り、決めた範囲を切り出す。dolly に頼らない)
- 保存の直し: `/workflow/save` は知らない引数ならエラーで何も保存しない。`path` も `file_path` として受ける
- ついでに直したもの: `/workflow/dialog/table_combo` と `/workflow/import_blender` のルートは、動かす関数が登録されていなかった(押しても "Unknown action")

自動で押す窓は **この 3 つだけ**: `Apply Character Preset` / `Apply Eyelash Elements`(Apply)、
「add a new layer or replace the current layer?」(Replace か Add)、「exit SkinGen editing mode?」(Yes か No)。
ライセンス・購入・ログイン・更新・規約・有効化・支払い・体験版の語がある窓は、**絶対に押しません**
(窓の全部の文字を調べます。ボタン・チェック・文章の箱・グループの題名も含む。日本語・韓国語・中国語・独仏西露の語も)。
そういう窓が開いている間は、ほかの窓も押しません。
押す窓の文字は**ふつうの英語だけ**です(ほかの文字の似た字が混じる窓は押さない)。CC5 の表示を日本語にしていると、押す窓として認識されません。

## 入れ直す手順

1. 渡すファイルは 5 つ: `cc5-plugin/` の `cc5_api.py`(更新)、`cc5_ui.py`、`cc5_uiview.py`、`cc5_skingen.py`、`cc5_content.py`。
   `server.py` と `main.py` は変えていないので、**CC5 の再起動は要りません**。
2. 入れる場所(金剛): `C:\Program Files\Reallusion\Character Creator 5\Bin64\OpenPlugin\CC5_MCP_Bridge\`
   - いつも `cc5_api.py` を入れている方法で、**5 つとも**入れる。
   - 金剛にリポジトリがあるなら `scripts\copy_to_installed.ps1`(`cc5_*.py` を全部コピーする形に直した)。
   - 新しく入れるなら `install-plugin.ps1`(これも `cc5_*.py` を全部コピーする)。
3. 反映: `curl http://127.0.0.1:5101/reload`(トンネル越し)。`success: true` が返れば済み。
   CC5 のコンソールに `helper module ... not loaded` が出ていないことを見る。
   `/reload` が 403 のときは、CC5 を `CC5_DEV_MODE=1` で起動し直す必要があります。撮影の合間にやってください。
4. 入ったかの確認: `curl -X POST http://127.0.0.1:5101/ui/job -d "{\"job_id\":\"x\"}"` が
   「unknown job」と返れば、ルートはあります。「helper modules are not installed」なら、ファイルが足りません。
5. MCP 側: `npm run build` 済み(`build/`)。Claude Code の MCP を再接続すると、新しい道具 9 個が見えます。

## 試す順番(上から。各行の「正しい姿」が出なければ止めて報告)

| # | することと道具 | 正しい姿 | 出なかったら |
|---|---|---|---|
| 0 | 窓を読む `list_cc5_windows`(または `python scripts/ui_client.py windows --shots 保存先 --main`) | 窓が無ければ "No pop-up windows"。窓があれば題名・ボタン・PNG | メイン窓の絵が真っ黒でも、3D ビューだけなら想定内(要確認) |
| 1 | 部品の名前 `find_ui_widgets object_name=qtModeSwitchPushButton visible_only=false`、`qtFeatureTableWidget`、`qtSpinBox` | 名前が見つかる | SkinGen の枠を一度開いてから。名前が違えば `cc5_skingen.py` の定数を直す |
| 2 | 型の一覧 `list_presets category=makeup_lip`、`eyelash_preset` | Nature などが出る。`1.HD Natural` の中の型も出る | `folders` と `errors` を見る(サブフォルダの返し方が名前か `$/` か未確認) |
| 3 | まつげの型 `apply_preset file_path=…\Avatar Preset\Eyelash\1.HD Natural\Curled.ccAvatarPreset watch_prefix=Lash_` | `answered` に apply。`watched` に新しい Lash_ の名前 | 「window needs a person」で止まったら、窓の題名を `list_cc5_windows` で見る。題名が上の 2 つと違う、ボタンが QPushButton でない、が原因の候補。`cc5_ui.py` の `WINDOW_RULES` を直す |
| 4 | 部品 2 つ `file_paths=[Wavy_Up.rlEyelashElement, Extended_Low.rlEyelashElement]` | 2 つ順に当たる | 同上 |
| 5 | 口紅 `apply_preset file_path=…\Lip Makeup\Rouge.ccSkinGenPreset` | `skingen.editor_active` が true、髪・帽子・まつげの部品が隠れる。2 本目以降は `answered` に replace | 「add/replace」の窓が違う形なら止まって報告される |
| 6 | 層 `skingen_state` → `skingen_layer action=hide index=0` → `show` → `select` | 一覧の visible が変わる(読み戻した値が返る) | 目のボタンは「チェック=隠れている」。逆なら `cc5_skingen.py` の `_set_eye` |
| 7 | **濃さ(誰も試していない)** `skingen_layer action=opacity index=0 opacity=50` | `opacity_before 100 → opacity_after 50`、画面の口紅が薄くなる | 数字だけ変わって絵が変わらないなら、`find_ui_widgets object_name=qtSpinBox visible_only=false` で箱が複数ないか見る。層を選び直して再度 |
| 8 | **消す(未試験・壊れてよい層で)** `skingen_layer action=delete index=1 confirm_delete=true` | `layers_before → layers_after` が 1 減る | 確認の窓が出たら**止まって報告**(自動では押さない)。メニューの名前が違えば `menu:` に一覧が出る |
| 9 | 焼き込み `skingen_editor active=false` | `answered: yes`、終わるまで待つ。そのあと髪などが戻る | 知らない窓が出たら止まって PNG つきで報告 |
| 10 | 保存の直し `curl -X POST …/workflow/save -d "{\"filename\":\"x\"}"` | error「unknown argument」、何も保存されない。`{"path":"新しい名前.ccProject"}` は新しい名前で保存 | |
| 11 | 撮影 `capture_framed_crop`(crop なし → あり) | 1 回目は縮小の全体図と `preview_scale`。測った箱を `crop` に入れると、毎回同じ大きさで切れる | 窓のスクリーンショットになったときは失敗として返る(大きさが違うため) |

## 窓が出たとき・仕事が長いとき

- 長い仕事(型を当てる・焼き込み・撮影)は「ジョブ」です。`Still running` と出たら、`get_ui_job job_id=… wait_seconds=60`。
- ジョブの間は、ほかのブリッジの命令は **「was NOT run」と断られます**(ロード中の CC5 に別の命令を入れると落ちる恐れがあるため)。
  読むだけの `list_cc5_windows` `find_ui_widgets` `skingen_state` `get_ui_job` は通ります。止めたいときは CC5 に環境変数 `CC5_UI_JOB_GUARD=0`。
- 「start request timed out」と出たら、**同じ命令をもう一度送らない**(CC5 が空いたあとに実行されることがあります)。まず窓と状態を見る。

## まだ分かっていないこと(正直な一覧)

- Apply の窓の本物の題名とボタンの種類。いまは 2 つの題名の完全一致だけを押す(ゆるくすると別の窓を押す恐れがあるため)。
- 窓が QDialog かどうか(違っても、題名が合えば押す作りにしてある)。
- メイン窓を `grab` したときの 3D ビュー(黒いかも。時間もかかるかも)。
- 削除の矢印メニューが開く前から中身を持っているか。確認の窓が出るか。
- 濃さの箱(`qtBlendOpacityHorizontalSliderEx` の `qtSpinBox`)が本当に効くか。
- `GetContentFoldersInFolder` が返すのが名前か `$/…` か(どちらでも動く作り)。
- 雲(未ダウンロード)の型は一覧に出ない。ダウンロードは人の仕事(Hub が前に出る)。
- この道具は本人のマウス操作と並べて使わない(層の部品は選ぶたびに作り直される)。

## 元に戻すとき

古い `cc5_api.py` に戻して `/reload` する。新しい 4 つのファイルが残っていても害はありません(使われないだけ)。

## 2026-10-30 の追加: ボタンを 1 つ押す(click_ui_button)と、exec の切りかえを 1 つに

これも**実機ではまだ試していません**(偽の Qt のテストだけ)。

- 足したもの: `cc5_uiclick.py`(新しい)。変えたもの: `cc5_api.py`・`cc5_ui.py`・`server.py`。
- 入れ方: `cc5_*.py` を全部と `server.py` を入れる。`install-plugin.ps1` なら両方入る。`scripts\copy_to_installed.ps1` は
  `cc5_*.py` だけなので、`server.py` は別に写す。
  - ボタンの道具は `/reload` で使えるようになる(`/reload` は `CC5_DEV_MODE=1` のときだけ)。
  - exec の新しい断りの文と `/health` の `exec_allowed` は `server.py` の変更なので、**CC5 の再起動が要る**。
- MCP 側: `npm run build` のあと Claude Code の MCP をつなぎ直すと、道具が 100 個になる(`click_ui_button` が増える)。

| # | すること | 正しい姿 |
|---|---|---|
| A | `check_cc5_connection` | `exec_python: off`(または ON)の行が出る。`unknown` なら、新しい `server.py` がまだ動いていない |
| B | `exec_python code="result=1"`(CC5 を `CC5_ALLOW_EXEC` なしで起動したとき) | 「decided ONLY by CC5_ALLOW_EXEC ...」で断られる。MCP 側の設定は関係ない |
| C | 壊れてよい窓で `click_ui_button window=<題名> text=<ふつうのボタン>` | `Pressed ...`、窓の絵、小窓の一覧。ボタンの働きが起きる |
| D | 同じ窓で、文字に Points / Delete などがあるボタンを指す | `refused: ... mentions 'point'` などで、何も押されない |
| E | 画面に鍵がかかった金剛で C をする | 押せる(マウスは効かないが Qt の click は効く、を確かめる) |
| F | Body Wrap の 💾▾ を `object_name` で指し、`menu_item` なし | 断られ、項目の一覧(Load Skeleton / Save Skeleton)が出る。ここで本当の objectName と項目の名前を記録する |
| G | 先に `POST /workflow/dialog/native {"enable": false}`、そのあと `menu_item="Save Skeleton"` | `click_returned: false` と保存の小窓が出る。`POST /workflow/dialog/file_fill {"path": 新しい名前, "save": true}` で保存し、`native` を true に戻す |

まだ分かっていないこと: Body Wrap の窓の本当の題名と objectName、💾 がメニュー付きの QToolButton か、メニューの中身が
開く前から入っているか(開くときに作るメニューなら「Entries: (empty)」と出て押せない)、Save Skeleton が Qt の
ファイルの小窓を開くか(Windows の小窓なら中から名前を入れられない)。
