# CC5 MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![MCP SDK](https://img.shields.io/badge/MCP%20SDK-1.29-green.svg)](https://github.com/modelcontextprotocol/sdk)

An MCP (Model Context Protocol) server that lets LLMs like Claude control **Reallusion Character Creator 5** through natural language. Adjust facial features, apply body presets, capture viewport screenshots, load assets, and export FBX files -- all via conversational commands.

## Architecture

```
┌─────────────┐     stdio      ┌──────────────────┐    HTTP :5101    ┌──────────────────┐     RLPy     ┌─────┐
│  LLM Client │ ◄────────────► │  MCP Server      │ ◄──────────────► │  CC5 Plugin      │ ◄──────────► │ CC5 │
│  (Claude)   │                │  (Node.js / TS)  │                  │  (Python / Qt)   │              │     │
└─────────────┘                └──────────────────┘                  └──────────────────┘              └─────┘
```

The MCP server communicates with Claude via **stdio** transport and forwards commands over **HTTP** to a Python plugin running inside CC5. The plugin executes all RLPy API calls on the main thread via a QTimer-driven command queue, ensuring thread safety.

## Features

### MCP Tools (59)

The MCP server provides 59 tools (registered in 16 modules under `src/tools/`) for controlling CC5. This list matches the code: there is one `server.tool(` call per tool in `src/tools/*.ts` (59 in total, all with unique names).

#### Scene & Avatar Management (8)
| Tool | Description |
|------|-------------|
| `check_cc5_connection` | Verify CC5 is running and the bridge plugin is active |
| `list_avatars` | List all avatars in the current scene |
| `get_scene_objects` | List all scene objects (avatars, props, lights, cameras) |
| `get_avatar_info` | Get avatar details including all non-zero morph values |
| `create_avatar` | Create a new neutral base avatar in the scene |
| `delete_avatar` | Delete an avatar by name, or all avatars |
| `capture_viewport` | Capture a screenshot of the CC5 3D viewport |
| `set_subdivision_level` | Set HD subdivision level (0 = base, 1 = medium, 2 = HD) |

#### Morph Controls & Character (7)
| Tool | Description |
|------|-------------|
| `search_morphs` | Search morph catalog by keyword |
| `adjust_morph` | Adjust a single morph slider (-1.0 to 1.0) |
| `adjust_multiple_morphs` | Batch-adjust multiple morph sliders at once |
| `get_morph_value` | Query the current value of a morph slider |
| `reset_morphs` | Reset all morphs to zero |
| `apply_body_preset` | Apply a body type preset (athletic, muscular, slim, heavy, average) |
| `describe_character` | Natural language description of current character appearance |

#### Facial Expressions & Profiles (5)
| Tool | Description |
|------|-------------|
| `get_expression_info` | Get available expression groups and sliders |
| `set_expression` | Set one or more expression sliders by name (weights 0.0-1.0) |
| `reset_expression` | Reset all expression sliders to neutral |
| `get_facial_profile` | Detect the current avatar's facial (expression) profile — authoritative RLPy profile type (CC5MetaHuman/CC4Extended/CC4Standard/Traditional), expression-set UID, per-category slider counts, and a heuristic ExPlus/HD/MetaHuman/Traditional class + ARKit capability. Read-only. |
| `convert_facial_profile` | Swap the active facial profile by loading a target `.ccFacialProfile` asset (`RIFacialProfileComponent.LoadProfile`). RLPy has no direct profile-type / one-click-ExPlus-upgrade API, so a pre-built target profile file is required. `dry_run` defaults to **true** (inspect + validate only). Intended as a temporary switch before export → convert back to a backup to restore. |

#### Content & Assets (9)
| Tool | Description |
|------|-------------|
| `list_clothes` | List clothing on the current avatar |
| `list_hair` | List hair on the current avatar |
| `list_accessories` | List accessories on the current avatar |
| `remove_scene_item` | Remove clothing, hair, or accessories by name |
| `set_item_visible` | Show or hide a scene item (clothing, hair, accessory, prop, light) |
| `browse_content` | Browse CC5 content folders (clothes, shoes, poses, motions, etc.) |
| `load_asset` | Load a CC5 asset file (.iAvatar, .ccm, .iClothes, etc.) |
| `export_fbx` | Export the current avatar as an FBX file. Mirrors the CC5 "Export FBX" dialog: `target_tool` preset, `export_motion` ("Mesh and Motion"), `sub_d_level` (HD subdivision), `embed_textures`, `fps`, `motion_range`, `convert_image_format`, `texture_size`. A bare filename exports into `D:\CC5Export` (override via `CC5_EXPORT_DIR`). |
| `create_actor_mixer` | Generate ActorMIXER PRO mixer assets (.ccMixerPreset) from the open avatar. `confirm_create` gates a dry-run (false, CANCELs) vs real creation (true). Requires the ActorMIXER PRO plugin. |

#### Materials & Shaders (9)
| Tool | Description |
|------|-------------|
| `get_material_info` | Get mesh and material names |
| `get_diffuse_color` | Get diffuse color of a material |
| `set_diffuse_color` | Set diffuse color (RGB, 0.0-1.0) |
| `get_material_properties` | Get opacity, glossiness, and specular values of a material |
| `set_material_opacity` | Set opacity (0.0 = transparent, 1.0 = opaque) |
| `set_material_glossiness` | Set glossiness (0.0 = matte, 1.0 = glossy) |
| `set_material_specular` | Set specular weight |
| `get_shader_parameters` | Get Digital Human Shader parameters of a material |
| `set_shader_parameter` | Set one Digital Human Shader parameter (skin roughness, SSS, micro-normal, ...) |

#### Colors (4)
| Tool | Description |
|------|-------------|
| `set_eye_color` | Set eye color (convenience shortcut) |
| `set_hair_color` | Set hair color (convenience shortcut) |
| `set_lip_color` | Set lip color (convenience shortcut) |
| `set_skin_color` | Set a uniform skin tone across all body skin materials |

#### Camera (3)
| Tool | Description |
|------|-------------|
| `get_camera_info` | Get camera position and focal length |
| `set_camera_focal_length` | Set camera focal length |
| `frame_camera` | Move the viewport camera to a preset view (face close-up, home, ...) |

#### Lighting (9)
| Tool | Description |
|------|-------------|
| `get_lights` | List all lights in the scene |
| `get_light_info` | Get color and multiplier of a named light |
| `set_light_color` | Set light color (RGB) |
| `set_light_multiplier` | Set light intensity multiplier |
| `set_light_active` | Turn a light on or off |
| `set_light_shadow` | Toggle shadow casting and/or set shadow darkness |
| `get_visual_settings` | Get ambient color and IBL state |
| `set_ambient` | Set the scene ambient (fill) light color |
| `set_ibl` | Enable/disable image-based lighting, optionally loading an HDRI |

#### Edit & History (2)
| Tool | Description |
|------|-------------|
| `undo` | Undo the last operation |
| `redo` | Redo an undone operation |

#### MetaHuman (2)
| Tool | Description |
|------|-------------|
| `bake_skin_textures` | Open CC5's Skin Editor / SkinGen "Bake Textures" workflow (Mesh-to-MetaHuman prep) |
| `export_head_metahuman` | Trigger CC5's "Export Head > Mesh to MetaHuman" pipeline (opens the dialog; you confirm output path and gender) |

#### Advanced (1)
| Tool | Description |
|------|-------------|
| `exec_python` | Execute Python code inside CC5's RLPy environment. **Off by default** -- works only when `CC5_ALLOW_EXEC=1` is set, see [Security](#security) |

### MCP Resources

| Resource URI | Description |
|-------------|-------------|
| `cc5://morphs/catalog` | Complete catalog of all morph sliders grouped by category |
| `cc5://avatar/current` | Current avatar state with all active morph values |

## Prerequisites

- **Node.js** 18+ and npm
- **Reallusion Character Creator 5** (CC5)
- **Windows** (CC5 is Windows-only)

## Quick Start

### 1. Build the MCP Server

```bash
git clone https://github.com/mackatwentytsuru/cc5-mcp-server.git
cd cc5-mcp-server
npm install
npm run build
```

### 2. Install the CC5 Plugin

Run in an **Administrator PowerShell**:

```powershell
powershell -ExecutionPolicy Bypass -File install-plugin.ps1
```

This copies the files of `cc5-plugin/` into CC5's `OpenPlugin\CC5_MCP_Bridge` directory (replacing an older install). Restart CC5 afterwards.

### 3. Configure Claude Code

Add to your `~/.claude.json` under `mcpServers` (a ready-made snippet is in `claude-mcp-config.json`):

```json
{
  "cc5": {
    "command": "node",
    "args": ["<path-to-project>/build/index.js"],
    "env": {
      "CC5_BRIDGE_URL": "http://127.0.0.1:5101"
    }
  }
}
```

Replace `<path-to-project>` with the absolute path to this repository.

`exec_python` and the silent Export Head routes are off by default. To use them, see [Security](#security).

### 4. Start the Bridge

**Option A: Automatic (recommended)** -- Launch CC5. The plugin loads automatically from `OpenPlugin/CC5_MCP_Bridge/`. Enable it in Plugin Manager if needed.

**Option B: Manual** -- In CC5, go to Script > Load Python and select `start_bridge.py`.

### 5. Verify Connection

Ask Claude: *"Check if CC5 is connected"* -- it will call `check_cc5_connection` and report the status.

## Usage Examples

### Create and customize a character

> "Create a new avatar and make them athletic with a slightly larger nose"

Claude will call:
1. `create_avatar` -- adds a base avatar
2. `apply_body_preset` with `preset: "athletic"`
3. `adjust_morph` with `morph_id: "Nose_Size"`, `value: 0.6`

### Describe and adjust

> "What does my character look like? Make the jaw wider."

Claude will call:
1. `describe_character` -- reads current morph state
2. `adjust_morph` with `morph_id: "Jaw_Width"`, `value: 0.7`

### Batch modifications

> "Give the character a rounder face with softer features"

Claude will call `adjust_multiple_morphs` with an array of morph adjustments for cheeks, jaw, chin, etc.

### Export for game engine

> "Export this character as FBX to my project folder"

Claude will call `export_fbx` with the specified output path.

The tool reproduces the CC5 "Export FBX (InstaLOD)" dialog. The recommended Unreal (UE5 Skeleton) call is:

```jsonc
{
  "output_path": "character.fbx",   // bare filename -> D:\CC5Export\character.fbx
  "target_tool": "UE5",             // Target Tool Preset: Unreal (UE5 Skeleton)
  "export_motion": true,            // FBX Options: Mesh and Motion
  "sub_d_level": 0,                  // HD Character Subdivision Level: SubD 0
  "embed_textures": true,           // Texture Settings: Embed Textures = ON
  "fps": 30                          // Include Motion: Frame Rate = 30 (Current Animation = All)
}
```

Passing a bare filename (no directory component) exports into `D:\CC5Export` by default — override the folder with the `CC5_EXPORT_DIR` environment variable. Absolute paths are used as-is. Omitting `motion_range` keeps the dialog default "All".

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `CC5_BRIDGE_URL` | `http://127.0.0.1:5101` | Full URL of the CC5 bridge HTTP server |
| `CC5_BRIDGE_PORT` | `5101` | Port for the bridge server (set in `cc5-plugin/main.py`) |
| `CC5_DEV_MODE` | `0` | Development helpers in the bridge plugin: `GET /reload` without a token and the full `GET /api` route list. Accepts `1`, `true` or `yes`. Read from the environment CC5 starts from. It does **not** enable code execution |
| `CC5_ALLOW_EXEC` | *(unset)* | Enables `exec_python` (`POST /exec/python`) and the silent Export Head routes (`POST /export/head_mh/silent/*`). Accepts `1`, `true` or `yes`. Set it for CC5 **and** for the MCP server -- see [Security](#security) |
| `CC5_RELOAD_SECRET` | *(empty)* | Auth token for the `/reload` endpoint. If set, requests must include `X-Reload-Token` header |
| `CC5_REQUEST_TIMEOUT_MS` | `30000` | HTTP request timeout in milliseconds (MCP server side) |
| `CC5_ROOT` | `C:\Program Files\Reallusion\Character Creator 5` | CC5 installation path (used for default avatar loading) |
| `CC5_EXPORT_DIR` | `D:\CC5Export` | Default output folder for `export_fbx` when given a bare filename (no directory). Read by the bridge plugin. |

## Development

### Build

```bash
npm run build        # Compile TypeScript
npm run dev          # Watch mode (recompiles on change)
```

### Test

```bash
npm test             # Run tests
npm run test:watch   # Watch mode
npm run test:coverage # With coverage report
npm run test:py      # Bridge plugin security tests (Python 3.10+, no CC5 needed)
```

Current suite: 513 Vitest tests in 16 files, plus 36 Python security tests.

### Hot-Reload the Python Plugin

The bridge supports hot-reloading `cc5_api.py` without restarting CC5. It is off by default: set `CC5_DEV_MODE=1` (or `CC5_RELOAD_SECRET`) in the environment CC5 starts from.

```bash
# Without auth
curl http://127.0.0.1:5101/reload

# With auth (when CC5_RELOAD_SECRET is set)
curl -H "X-Reload-Token: <secret>" http://127.0.0.1:5101/reload
```

After reloading, the server's dispatch table is automatically patched with the updated functions.

### Project Structure

```
cc5-mcp-server/
├── src/                    # MCP Server (TypeScript)
│   ├── index.ts            # Entry point
│   ├── cc5-bridge.ts       # HTTP client for CC5 bridge
│   ├── types.ts            # Type definitions
│   ├── util.ts             # Shared utilities (bridgeCall wrapper)
│   ├── tools/              # MCP tool definitions (16 files, 59 tools total)
│   │   ├── morph.ts        # Morph search, adjust, reset (5 tools)
│   │   ├── scene.ts        # Scene/avatar management, viewport, subdivision (7 tools)
│   │   ├── asset.ts        # Asset loading / FBX export (2 tools)
│   │   ├── actor-mixer.ts  # ActorMIXER PRO mixer assets (1 tool)
│   │   ├── character.ts    # Body presets, character description (2 tools)
│   │   ├── content.ts      # Clothes, hair, accessories, browse (5 tools)
│   │   ├── color.ts        # Eye, hair, lip, skin color setters (4 tools)
│   │   ├── material.ts     # Material info, colors, properties, shader parameters (9 tools)
│   │   ├── camera.ts       # Camera info, focal length, framing (3 tools)
│   │   ├── light.ts        # Lights, ambient, IBL (9 tools)
│   │   ├── visibility.ts   # Show/hide items, scene objects (2 tools)
│   │   ├── edit.ts         # Undo/redo (2 tools)
│   │   ├── expression.ts   # Expression info, set, reset (3 tools)
│   │   ├── facial-profile.ts # Facial profile detect + convert (2 tools)
│   │   ├── scripting.ts    # Python execution (1 tool)
│   │   └── metahuman.ts    # MetaHuman export (2 tools)
│   └── resources/
│       └── morphs.ts       # Morph catalog & avatar state resources
├── cc5-plugin/             # CC5 Python plugin
│   ├── main.py             # Plugin entry (initialize_plugin / uninitialize_plugin)
│   ├── server.py           # HTTP bridge server (http.server)
│   ├── cc5_api.py          # RLPy API wrapper
│   └── config.json         # Plugin configuration
├── tests/                  # Vitest unit tests; tests/python = bridge security tests
├── start_bridge.py         # Manual bridge startup script
├── install-plugin.ps1      # Plugin installer (requires admin)
└── claude-mcp-config.json  # Claude Code MCP config snippet
```

## API Reference

The bridge exposes one HTTP route per tool. The tables below list the core routes; the complete route table is `GET_ROUTES` / `POST_ROUTES` in `cc5-plugin/server.py` (and `GET /api` returns it when `CC5_DEV_MODE=1`).

### GET Endpoints

| Endpoint | Description | Response |
|----------|-------------|----------|
| `GET /health` | Health check | `{"result": {"status": "ok", "service": "cc5-mcp-bridge", "version": "..."}}` |
| `GET /api` | API discovery (all endpoints and required params, dev mode) | `{"result": {"service": "...", "endpoints": {...}}}` |
| `GET /reload` | Hot-reload cc5_api module (needs `CC5_DEV_MODE=1` or `CC5_RELOAD_SECRET`) | `{"result": {"success": true}}` |
| `GET /avatars` | List all scene avatars | `{"result": [{"name": "...", "id": "...", "type": "..."}]}` |
| `GET /avatar/info` | Current avatar details + active morphs | `{"result": {"name": "...", "active_morphs": {...}}}` |
| `GET /morphs/catalog` | Full morph catalog grouped by category | `{"result": {"Category": [{"id": "...", "display_name": "..."}]}}` |
| `GET /facial/profile` | Current avatar's facial-profile detection (read-only) | `{"result": {"profile_type": "CC5MetaHuman", "expression_set_uid": "...", "total_sliders": 379, "heuristic_class": "...", "arkit_capable": true}}` |

### POST Endpoints

| Endpoint | Parameters | Description |
|----------|-----------|-------------|
| `POST /morph/get` | `morph_id` | Get current morph value |
| `POST /morph/set` | `morph_id`, `value` | Set a morph slider (-1.0 to 1.0) |
| `POST /morphs/set` | `morphs` (array of `{id, value}`) | Set multiple morphs at once (-1.0 to 1.0 each) |
| `POST /avatar/create` | *(none)* | Create a default CC3+ avatar |
| `POST /asset/load` | `file_path` | Load a CC5 asset file |
| `POST /export/fbx` | `output_path`, `options` (optional) | Export avatar as FBX |
| `POST /facial/profile/convert` | `target_profile_path`, `dry_run` (default true), `backup_current_to` (optional) | Swap facial profile via LoadProfile of a target `.ccFacialProfile`. `dry_run=true` inspects/validates only |
| `POST /viewport/capture` | `output_path` (optional) | Capture viewport screenshot |
| `POST /subdivision` | `level` (0-2) | Set HD subdivision level |

All responses follow the envelope format: `{"result": ...}` on success, `{"error": "..."}` on failure.

## Security

The bridge is a local HTTP server running inside CC5. It has these protections:

- **Localhost only** -- The bridge server binds exclusively to `127.0.0.1`. The MCP server validates that `CC5_BRIDGE_URL` points to localhost before connecting.
- **Host check (DNS rebinding)** -- Every request must carry `Host: 127.0.0.1:<port>`, `localhost:<port>` or `[::1]:<port>`, with the bridge's own port. A web page that points its own domain at 127.0.0.1 still sends its own domain name, so it gets HTTP 403.
- **No requests from web pages** -- Requests with an `Origin` header, or with a `Sec-Fetch-Site` header other than `none`, get HTTP 403. Browsers add these headers to requests made by web pages (including form posts and `<img>` loads); curl, Python, PowerShell and the MCP server do not send them. The bridge sends no CORS headers.
- **Risky features are off by default** -- see the next section.
- **Path validation** -- Both the TypeScript MCP server and the Python plugin validate file paths to prevent path traversal (`..`) attacks. Only allowed file extensions are accepted for asset loading and export.
- **Reload authentication** -- The `/reload` endpoint supports token-based auth via the `CC5_RELOAD_SECRET` environment variable and `X-Reload-Token` header.
- **Request size limits** -- The bridge enforces a 1 MB maximum request body size.
- **Thread safety** -- All RLPy API calls are serialized through a command queue and executed on CC5's main thread via QTimer.

### Off by default

| Feature | What it does | Turned on by |
|---------|--------------|--------------|
| `exec_python` tool / `POST /exec/python` | Runs any Python code inside CC5 | `CC5_ALLOW_EXEC=1` |
| `POST /export/head_mh/silent/*` (4 routes) | Drives CC5's Export Head dialogs and types the save path with simulated keystrokes, without asking you | `CC5_ALLOW_EXEC=1` |
| `GET /reload` without a token, full `GET /api` route list | Development helpers | `CC5_DEV_MODE=1` |

Neither `CC5_DEV_MODE` nor `CC5_RELOAD_SECRET` enables code execution. While a feature is off, the bridge answers HTTP 403 and the MCP tool returns an error; both explain how to turn it on. When the plugin starts, CC5's Python console prints which of these are on.

### Turning on exec_python and the silent Export Head routes

`CC5_ALLOW_EXEC` must be set in two places, because CC5 and the MCP server each read their own environment:

1. **For CC5 (the bridge plugin)** -- set it for your Windows user, then restart CC5:
   ```powershell
   setx CC5_ALLOW_EXEC 1
   ```
   `setx` only reaches programs started after it. Start CC5 from the Start menu or from a new terminal; a terminal or app that was already open keeps its old environment until it is restarted.
2. **For the MCP server** -- add it to the server's `env` (needed for the `exec_python` tool; the silent routes are called on the bridge directly, so they only need step 1):
   ```json
   "env": { "CC5_BRIDGE_URL": "http://127.0.0.1:5101", "CC5_ALLOW_EXEC": "1" }
   ```

To turn it off again, remove both settings and restart CC5 and your MCP client. For the Windows user variable:

```powershell
[Environment]::SetEnvironmentVariable("CC5_ALLOW_EXEC", $null, "User")
```

### What turning it on risks

- Any program running on your computer under your account, and anything that can make the LLM call `exec_python` (for example instructions hidden in a file or web page the model reads), can run code inside CC5 with your user's permissions: read and write your files, start programs, use the network.
- The silent Export Head routes send keystrokes to the window in front. If another window comes to the front while they run, the keystrokes go there.
- The Host and Origin checks stop web pages, not other programs on the same computer. Only turn this on for a computer you trust, never make port 5101 reachable from other computers (no port forwarding or proxies), and turn it off when you do not need it.

### Upgrading from 1.1.x

- `exec_python` used to be on by default (through `CC5_DEV_MODE`, which defaulted to `1`). It is now off until you set `CC5_ALLOW_EXEC=1` as described above.
- `CC5_DEV_MODE` now defaults to `0`. Set `CC5_DEV_MODE=1` for CC5 if you use `GET /reload` while working on the plugin.
- Rebuild the MCP server (`npm run build`), reinstall the plugin and restart CC5. `GET /health` reports `"version": "1.2.0"` once the new plugin is running. Note that `install-plugin.ps1` replaces the whole `CC5_MCP_Bridge` folder, so move anything you keep in it first.

## セキュリティ(日本語)

ブリッジは、CC5 の中で動くローカルの HTTP サーバーです。次の守りが入っています。

- **このパソコンの中だけ** -- ブリッジは `127.0.0.1` だけで待ち受けます。MCP サーバーは、localhost 以外を指す `CC5_BRIDGE_URL` を受け付けません。
- **Host の確認(DNS リバインディング対策)** -- Host ヘッダーが `127.0.0.1:<ポート>`・`localhost:<ポート>`・`[::1]:<ポート>`(ブリッジ自身のポート)でないリクエストは、HTTP 403 で断ります。自分のドメインを 127.0.0.1 に向けた Web ページは、自分のドメイン名を送ってくるので、ここで止まります。
- **Web ページからのリクエストを断る** -- `Origin` ヘッダーがある、または `Sec-Fetch-Site` が `none` 以外のリクエストは、HTTP 403 で断ります。ブラウザーは、Web ページが出すリクエスト(フォームの送信や `<img>` の読み込みを含む)にこれらを付けます。curl・Python・PowerShell・MCP サーバーは付けません。CORS のヘッダーも返しません。
- **危ない機能は初期状態で無効** -- 下の表のとおりです。
- パスの検査、`/reload` のトークン認証、1 MB の上限、CC5 のメインスレッドでの実行は、これまでどおりです。

### 初期状態で無効なもの

| 機能 | すること | 有効にする設定 |
|------|---------|----------------|
| `exec_python` ツール / `POST /exec/python` | CC5 の中で、どんな Python コードでも動かす | `CC5_ALLOW_EXEC=1` |
| `POST /export/head_mh/silent/*`(4 つ) | CC5 の Export Head の画面を自動で操作し、保存先をキー入力で打ち込む(確認なし) | `CC5_ALLOW_EXEC=1` |
| トークンなしの `GET /reload`、`GET /api` の全ルート一覧 | 開発用の機能 | `CC5_DEV_MODE=1` |

`CC5_DEV_MODE` や `CC5_RELOAD_SECRET` では、コードの実行は有効になりません。無効のあいだは、ブリッジは HTTP 403、MCP ツールはエラーを返し、どうすれば有効にできるかを知らせます。プラグインが起動すると、CC5 の Python コンソールに、どれが有効かが表示されます。

### exec_python と silent ルートを有効にする

`CC5_ALLOW_EXEC` は 2 か所に設定します。CC5 と MCP サーバーは、それぞれ自分の環境変数を読むからです。

1. **CC5(ブリッジ)用** -- Windows のユーザー環境変数に設定して、CC5 を再起動します。
   ```powershell
   setx CC5_ALLOW_EXEC 1
   ```
   `setx` は、このあとに起動したプログラムにだけ効きます。CC5 はスタートメニューか、新しく開いたターミナルから起動してください。前から開いているターミナルやアプリは、再起動するまで古い設定のままです。
2. **MCP サーバー用** -- サーバーの `env` に足します(`exec_python` ツールに必要です。silent ルートはブリッジを直接呼ぶので、1 だけで動きます)。
   ```json
   "env": { "CC5_BRIDGE_URL": "http://127.0.0.1:5101", "CC5_ALLOW_EXEC": "1" }
   ```

無効に戻すときは、両方の設定を消して、CC5 と MCP クライアントを再起動します。Windows のユーザー環境変数は次のコマンドで消せます。

```powershell
[Environment]::SetEnvironmentVariable("CC5_ALLOW_EXEC", $null, "User")
```

### 有効にすると何が危ないか

- このパソコンで同じユーザーとして動くプログラムや、LLM に `exec_python` を呼ばせられるもの(たとえば、モデルが読むファイルや Web ページに隠された指示)が、CC5 の中でコードを動かせるようになります。あなたのユーザーの権限でできること(ファイルの読み書き、プログラムの起動、ネットへの通信)は、全部できてしまいます。
- silent ルートは、いちばん前のウィンドウにキー入力を送ります。動いているあいだに別のウィンドウが前に出ると、そちらに入力されます。
- Host と Origin の確認で防げるのは Web ページだけです。同じパソコンの中の別のプログラムは防げません。信頼できるパソコンでだけ有効にし、ポート 5101 をほかのパソコンから届くようにしないでください(ポートの転送やプロキシをしない)。使わないときは無効に戻してください。

### 1.1.x からの更新

- これまでは `CC5_DEV_MODE` の初期値が `1` だったため、`exec_python` が初期状態で有効でした。今は、上のとおり `CC5_ALLOW_EXEC=1` を設定するまで無効です。
- `CC5_DEV_MODE` の初期値は `0` になりました。プラグインの開発で `GET /reload` を使うときは、CC5 用に `CC5_DEV_MODE=1` を設定してください。
- MCP サーバーを作り直し(`npm run build`)、プラグインを入れ直して、CC5 を再起動します。新しいプラグインが動いていれば、`GET /health` が `"version": "1.2.0"` を返します。`install-plugin.ps1` は `CC5_MCP_Bridge` フォルダーを丸ごと入れ替えるので、そこに置いているものは先に移してください。

## License

[MIT](LICENSE) © Yuki Tsuruoka

---

Made by Yuki Tsuruoka — stage visuals and live show production, building tools with Claude Code. Web: [otolume.com](https://otolume.com) / Instagram: [@tsuru614](https://www.instagram.com/tsuru614/) / YouTube: [channel](https://www.youtube.com/channel/UCYngpwyo7vGBIXBtKhh7z1g)

制作: Yuki Tsuruoka — ステージ映像とライブ演出の制作。Claude Code でツールを作っています。Web: [otolume.com](https://otolume.com) / Instagram: [@tsuru614](https://www.instagram.com/tsuru614/) / YouTube: [チャンネル](https://www.youtube.com/channel/UCYngpwyo7vGBIXBtKhh7z1g)
