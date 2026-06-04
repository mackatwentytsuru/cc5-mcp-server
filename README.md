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

### MCP Tools (44)

The MCP server provides 44 tools across 14 modules for controlling CC5:

#### Scene & Avatar Management
| Tool | Description |
|------|-------------|
| `check_cc5_connection` | Verify CC5 is running and the bridge plugin is active |
| `list_avatars` | List all avatars in the current scene |
| `list_scene_objects` | List all scene objects (avatars, props, lights, cameras) |
| `get_avatar_info` | Get avatar details including all non-zero morph values |
| `create_avatar` | Create a new CC3+ base avatar in the scene |
| `describe_character` | Natural language description of current character appearance |

#### Morph Controls
| Tool | Description |
|------|-------------|
| `search_morphs` | Search morph catalog by keyword |
| `adjust_morph` | Adjust a single morph slider (-1.0 to 1.0) |
| `adjust_multiple_morphs` | Batch-adjust multiple morph sliders at once |
| `get_morph_value` | Query the current value of a morph slider |
| `reset_morphs` | Reset all morphs to zero |
| `apply_body_preset` | Apply a body type preset (athletic, muscular, slim, heavy, average) |

#### Content & Assets
| Tool | Description |
|------|-------------|
| `list_clothes` | List clothing on the current avatar |
| `list_hair` | List hair on the current avatar |
| `list_accessories` | List accessories on the current avatar |
| `remove_scene_item` | Remove clothing, hair, or accessories by name |
| `browse_content` | Browse CC5 content folders (clothes, shoes, etc.) |
| `load_asset` | Load a CC5 asset file (.iAvatar, .ccm, .iClothes, etc.) |
| `export_fbx` | Export the current avatar as an FBX file |

#### Materials & Colors
| Tool | Description |
|------|-------------|
| `get_material_info` | Get mesh and material names |
| `get_diffuse_color` | Get diffuse color of a material |
| `set_diffuse_color` | Set diffuse color (RGB, 0.0-1.0) |
| `set_eye_color` | Set eye color (convenience shortcut) |
| `set_hair_color` | Set hair color (convenience shortcut) |
| `set_lip_color` | Set lip color (convenience shortcut) |

#### Visibility & Display
| Tool | Description |
|------|-------------|
| `set_item_visible` | Show or hide scene items |

#### Camera & Lighting
| Tool | Description |
|------|-------------|
| `get_camera_info` | Get camera position and focal length |
| `set_camera_focal_length` | Set camera focal length |
| `get_lights` | List all lights in the scene |
| `set_light_color` | Set light color (RGB) |

#### Expression & Animation
| Tool | Description |
|------|-------------|
| `get_expression_info` | Get available expression groups and sliders |

#### Rendering & Export
| Tool | Description |
|------|-------------|
| `capture_viewport` | Capture a screenshot of the CC5 3D viewport |
| `set_subdivision_level` | Set HD subdivision level (0 = base, 1 = medium, 2 = HD) |

#### Edit & History
| Tool | Description |
|------|-------------|
| `undo` | Undo the last operation |
| `redo` | Redo an undone operation |

#### Advanced Features
| Tool | Description |
|------|-------------|
| `execute_python` | Execute Python code in CC5 (dev mode only) |
| `execute_rlpy` | Execute RLPy API calls directly (dev mode only) |
| `metahuman_export` | Export to MetaHuman (when available) |

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
git clone <repo-url> cc5-mcp-server
cd cc5-mcp-server
npm install
npm run build
```

### 2. Install the CC5 Plugin

Run in an **Administrator PowerShell**:

```powershell
powershell -ExecutionPolicy Bypass -File install-plugin.ps1
```

This creates a symlink from CC5's OpenPlugin directory to the `cc5-plugin/` folder.

### 3. Configure Claude Code

Add to your `~/.claude.json` under `mcpServers`:

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

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `CC5_BRIDGE_URL` | `http://127.0.0.1:5101` | Full URL of the CC5 bridge HTTP server |
| `CC5_BRIDGE_PORT` | `5101` | Port for the bridge server (set in `cc5-plugin/main.py`) |
| `CC5_DEV_MODE` | `1` | Enable hot-reload (`/reload` endpoint) and dev surfaces (0 = production, 1 = development) |
| `CC5_ALLOW_EXEC` | *(unset)* | Enable `/exec/python` and `/exec/rlpy` endpoints (only active when set, regardless of DEV_MODE) |
| `CC5_RELOAD_SECRET` | *(empty)* | Auth token for the `/reload` endpoint. If set, requests must include `X-Reload-Token` header |
| `CC5_REQUEST_TIMEOUT_MS` | `30000` | HTTP request timeout in milliseconds (MCP server side) |
| `CC5_ROOT` | `C:\Program Files\Reallusion\Character Creator 5` | CC5 installation path (used for default avatar loading) |

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
│   ├── tools/              # MCP tool definitions (14 files, 44 tools total)
│   │   ├── morph.ts        # Morph search, adjust, reset (5 tools)
│   │   ├── scene.ts        # Scene/avatar management (6 tools)
│   │   ├── asset.ts        # Asset loading / FBX export (2 tools)
│   │   ├── character.ts    # Body presets, character description (2 tools)
│   │   ├── content.ts      # Clothes, hair, accessories, browse (5 tools)
│   │   ├── color.ts        # Eye, hair, lip color setters (3 tools)
│   │   ├── material.ts     # Material info, diffuse color (7 tools)
│   │   ├── camera.ts       # Camera focal length control (2 tools)
│   │   ├── light.ts        # Light color and info (4 tools)
│   │   ├── visibility.ts   # Show/hide items (2 tools)
│   │   ├── edit.ts         # Undo/redo (2 tools)
│   │   ├── expression.ts   # Expression info (1 tool)
│   │   ├── scripting.ts    # Python/RLPy execution (1 tool)
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

### GET Endpoints

| Endpoint | Description | Response |
|----------|-------------|----------|
| `GET /health` | Health check | `{"result": {"status": "ok", "service": "cc5-mcp-bridge", "version": "..."}}` |
| `GET /api` | API discovery (all endpoints and required params) | `{"result": {"service": "...", "endpoints": {...}}}` |
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

## License

MIT
