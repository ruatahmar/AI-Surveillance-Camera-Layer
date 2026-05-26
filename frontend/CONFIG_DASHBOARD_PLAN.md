# Config Dashboard + Hot-Reload Plan

## Architecture

```
 Dashboard UI  ←─→  /api/config (GET/PATCH)  ──writes──→  config.toml  ──mtime poll──→  Python Backend
 (Next.js)           (Next.js API route)                      (disk)                     (hot-reloads
                                                                                         VideoProcessors)
```

## Config File Path

`../../config.toml` relative to Next.js server root (`frontend/`). Overridable via `CONFIG_PATH` env var.

## API: `frontend/app/api/config/route.ts`

### GET
Reads `config.toml`, parses with `smol-toml`, returns JSON.

### PATCH
Accepts partial/full config JSON, deep-merges into currently parsed TOML object, stringifies back to TOML, writes to disk.

## Config Change Classification

| Category | Fields | Action |
|----------|--------|--------|
| **tunable** | `conf_threshold`, `loitering_enabled`, `loitering_threshold`, `loitering_windows`, `loitering_alert_limit`, `alert_limit_per_track`, `alert_cooldown`, `no_id_alert_distance`, `alert_confirm_frames`, `process_every_n_frames`, `crowd_min_people`, `crowd_min_duration`, `green_lanyard_enabled`, `lanyard_green_threshold` | Update in-place on `VideoProcessor` at runtime |
| **restart** | `model_path`, `source` (camera URL/index), adding/removing sources | Log "restart required"; mark in UI with tooltip |

## Backend Changes

### `app/core/config.py`
- Add `diff()` — compares two `Config` instances, returns categorized changes

### `app/core/config_watcher.py` (new)
- Polls `config.toml` mtime every 3s
- On change: reloads config, calls `diff()`, invokes registered callbacks with `(new_config, changes)`

### `main.py`
- Start `ConfigWatcher` after `_start_processors()`
- On change: iterate `VideoProcessor` instances and apply tunable updates

### `app/core/processor.py`
- Add `apply_tunable(source_config)` — updates `self.config`, detector conf, loitering threshold, crowd params, lanyard settings in-place

## Frontend Changes

### Dependency
- `npm install smol-toml` — TOML parse/stringify for JS

### UI: Add to `frontend/app/page.tsx`
- Settings button opens a modal/panel
- General section: `model_path`, `conf_threshold`, `loitering_threshold`
- Per-source cards: all tunable fields as inputs/toggles/sliders
- Save button → `PATCH /api/config`
- Restart-required fields show "(requires restart)" tooltip
- Status indicator: last saved time

## Edge Cases
- **TOML comments**: `smol-toml` loses comments on write. `config.toml.example` is reference.
- **Concurrent edits**: Last write wins. Acceptable.
- **Polling latency**: ≤3s before hot-reload applies.
- **YOLO model reload**: `model_path` change = restart required (heavy operation).
- **Source reconnection**: Camera URL/index change = restart required (needs stream reopen).

## Known Frontend Gaps (from current `page.tsx`)

### Missing alert labels
`wrong_lanyard` is emitted by the Python backend (`processor._handle_id_alerts` / `_label_people`) but has no entry in `labelStyles` or `labelText` maps on the frontend. It currently falls through to the `unknown` style. Fix: add `wrong_lanyard` entries.

### Color coding
Alert cards use `labelStyles` for per-label coloring, but `wrong_lanyard` is missing. Stat pills filter by `"no_id"`, `"loitering"`, `"crowd"` — add `"wrong_lanyard"` and `"green_lanyard"` pills. Also consider distinct colors: orange for wrong_lanyard, green for green_lanyard, to distinguish from the "bad" red categories.

Suggestion:
| Label | Color |
|-------|-------|
| `no_id` | red |
| `loitering` | red |
| `crowd` | blue |
| `wrong_lanyard` | orange/amber |
| `green_lanyard` | green |
| `Cards` | green (already there) |
| `Lanyard` | blue (already there) |

### Live video stream (low priority)
Stream processed frames from the Python backend to the frontend in real time. Options:
- **WebSocket**: Python pushes JPEG frames via WebSocket, frontend renders in `<img>` or `<canvas>`. Requires a WebSocket server on the Python side (e.g., `websockets` library, or embed a simple WS handler).
- **HTTP MJPEG**: Python serves `/video_feed` endpoints (one per source) using OpenCV's video writing + Flask's streaming response. Frontend uses `<img src="/video_feed/Webcam">`.
- **Polling**: Python saves latest frame to disk / in-memory buffer, frontend polls every ~500ms. Simplest but least smooth.

Given the current architecture (no Python web server), this is a significant lift — requires either adding a web/WS server to the Python backend or a different streaming approach. Defer until core config dashboard is complete.
