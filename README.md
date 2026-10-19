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

### MCP Tools (57)

The MCP server provides 57 tools (registered in 15 modules under `src/tools/`) for controlling CC5. This list matches the code: there is one `server.tool(` call per tool in `src/tools/*.ts` (57 in total, all with unique names).

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

#### Facial Expressions (3)
| Tool | Description |
|------|-------------|
| `get_expression_info` | Get available expression groups and sliders |
| `set_expression` | Set one or more expression sliders by name (weights 0.0-1.0) |
| `reset_expression` | Reset all expression sliders to neutral |

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
| `exec_python` | Execute Python code inside CC5's RLPy environment. Available when `CC5_DEV_MODE=1` (the default) or `CC5_ALLOW_EXEC=1` is set -- see [Security](#security) |

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
| `CC5_DEV_MODE` | `1` | Development mode (0 = production, 1 = development). In development mode the `/reload` endpoint, the `/api` endpoint listing and the `/exec/python` endpoint are enabled |
| `CC5_ALLOW_EXEC` | *(unset)* | Enable the `/exec/python` endpoint (the `exec_python` tool) when `CC5_DEV_MODE` is not 1. Accepts `1`, `true` or `yes` |
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
```

### Hot-Reload the Python Plugin

The bridge supports hot-reloading `cc5_api.py` without restarting CC5:

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
│   ├── tools/              # MCP tool definitions (15 files, 57 tools total)
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
│   │   ├── scripting.ts    # Python execution (1 tool)
│   │   └── metahuman.ts    # MetaHuman export (2 tools)
│   └── resources/
│       └── morphs.ts       # Morph catalog & avatar state resources
├── cc5-plugin/             # CC5 Python plugin
│   ├── main.py             # Plugin entry (initialize_plugin / uninitialize_plugin)
│   ├── server.py           # HTTP bridge server (http.server)
│   ├── cc5_api.py          # RLPy API wrapper
│   └── config.json         # Plugin configuration
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
| `GET /reload` | Hot-reload cc5_api module | `{"result": {"success": true}}` |
| `GET /avatars` | List all scene avatars | `{"result": [{"name": "...", "id": "...", "type": "..."}]}` |
| `GET /avatar/info` | Current avatar details + active morphs | `{"result": {"name": "...", "active_morphs": {...}}}` |
| `GET /morphs/catalog` | Full morph catalog grouped by category | `{"result": {"Category": [{"id": "...", "display_name": "..."}]}}` |

### POST Endpoints

| Endpoint | Parameters | Description |
|----------|-----------|-------------|
| `POST /morph/get` | `morph_id` | Get current morph value |
| `POST /morph/set` | `morph_id`, `value` | Set a morph slider (-1.0 to 1.0) |
| `POST /morphs/set` | `morphs` (array of `{id, value}`) | Set multiple morphs at once (-1.0 to 1.0 each) |
| `POST /avatar/create` | *(none)* | Create a default CC3+ avatar |
| `POST /asset/load` | `file_path` | Load a CC5 asset file |
| `POST /export/fbx` | `output_path`, `options` (optional) | Export avatar as FBX |
| `POST /viewport/capture` | `output_path` (optional) | Capture viewport screenshot |
| `POST /subdivision` | `level` (0-2) | Set HD subdivision level |

All responses follow the envelope format: `{"result": ...}` on success, `{"error": "..."}` on failure.

## Security

- **Localhost only** -- The bridge server binds exclusively to `127.0.0.1`. The MCP server validates that `CC5_BRIDGE_URL` points to localhost before connecting.
- **Path validation** -- Both the TypeScript MCP server and the Python plugin validate file paths to prevent path traversal (`..`) attacks. Only allowed file extensions are accepted for asset loading and export.
- **Reload authentication** -- The `/reload` endpoint supports token-based auth via the `CC5_RELOAD_SECRET` environment variable and `X-Reload-Token` header.
- **Request size limits** -- The bridge enforces a 1 MB maximum request body size.
- **Thread safety** -- All RLPy API calls are serialized through a command queue and executed on CC5's main thread via QTimer.
- **Code execution** -- `exec_python` runs arbitrary Python inside CC5. It is enabled by default because `CC5_DEV_MODE` defaults to `1`. If other software or web pages on the same computer should not be able to reach the bridge, set `CC5_DEV_MODE=0` (and leave `CC5_ALLOW_EXEC` unset) in the environment CC5 is started from.

## License

[MIT](LICENSE) © Yuki Tsuruoka

---

Made by Yuki Tsuruoka — stage visuals and live show production, building tools with Claude Code. Web: [otolume.com](https://otolume.com) / Instagram: [@tsuru614](https://www.instagram.com/tsuru614/) / YouTube: [channel](https://www.youtube.com/channel/UCYngpwyo7vGBIXBtKhh7z1g)

制作: Yuki Tsuruoka — ステージ映像とライブ演出の制作。Claude Code でツールを作っています。Web: [otolume.com](https://otolume.com) / Instagram: [@tsuru614](https://www.instagram.com/tsuru614/) / YouTube: [チャンネル](https://www.youtube.com/channel/UCYngpwyo7vGBIXBtKhh7z1g)
